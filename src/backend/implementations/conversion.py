"""
Handling of converting files to a different format.
"""

from collections.abc import Iterator
from itertools import chain

from backend.base.definitions import FileExtraInfo
from backend.base.helpers import PortablePool, filtered_iter
from backend.implementations.converters import (
    ConvertersManager,
    ProposedConversion,
)
from backend.implementations.volumes import Volume, scan_files
from backend.internals.db import commit
from backend.internals.db_models import FilesDB
from backend.internals.server import TaskStatusEvent, WebSocket


def _get_convertable_files(
    volume_id: int, issue_id: int | None = None, filepath_filter: list[str] = []
) -> Iterator[ProposedConversion]:
    """Get the files of a volume or issue that can be converted to a format that
    is more desired according to the format preference and extraction settings.

    Args:
        volume_id (int): The ID of the volume.
        issue_id (Union[int, None], optional): The ID of the issue.
            Defaults to None.
        filepath_filter (list[str], optional): Only convert files mentioned in
            this list.
            Defaults to [].

    Yields:
        Iterator[ProposedConversion]: The proposed conversions of files to
            another format.
    """
    if issue_id:
        file_list = Volume(volume_id).get_issue(issue_id).get_files()
    else:
        file_list = Volume(volume_id).get_all_files()

    for file in sorted(
        filtered_iter((f["filepath"] for f in file_list), set(filepath_filter))
    ):
        conversion_proposal = ConvertersManager.select_converter(file)
        if conversion_proposal is None:
            continue

        yield conversion_proposal

    return


def preview_mass_convert(
    volume_id: int,
    issue_id: int | None = None,
    is_for_api: bool = False,
) -> dict[str, str] | list[dict[str, str | int]]:
    """Get a list of suggested conversions for a volume or issue.

    Args:
        volume_id (int): The ID of the volume to check for.
        issue_id (Union[int, None], optional): The ID of the issue to check for.
            Defaults to None.

    Returns:
        Dict[str, str]: Mapping of filename before to after conversion.
    """
    volume = Volume(volume_id)

    volume_folder = volume.vd.folder

    result: dict[str, str] = {
        p.filepath: p.new_filepath or volume_folder
        for p in _get_convertable_files(volume_id, issue_id)
    }

    if is_for_api:
        if not issue_id:
            issues = volume.get_issues()
            return [
                {
                    "id": next(
                        (
                            x
                            for x in issues
                            if x.calculated_issue_number
                            == FilesDB.issues_covered(key)[0]
                        ),
                        issues[0],
                    ).id,
                    "existingPath": key,
                    "newPath": result[key],
                }
                for key in result
            ]
        else:
            return [
                {"id": issue_id, "existingPath": key, "newPath": result[key]}
                for key in result
            ]

    return result


def mass_convert(
    volume_id: int,
    issue_id: int | None = None,
    filepath_filter: list[str] = [],
    update_websocket_progress: bool = False,
    update_websocket_files: bool = False,
    file_extra_info: FileExtraInfo | None = None,
) -> list[str]:
    """Convert files for a volume or issue.

    Args:
        volume_id (int): The ID of the volume to convert for.

        issue_id (Union[int, None], optional): The ID of the issue to convert for.
            Defaults to None.

        filepath_filter (List[str], optional): Only convert files
        mentioned in this list.
            Defaults to [].

        update_websocket_progress (bool, optional): Send task progress updates
        over the websocket.
            Defaults to False.

        update_websocket_files (bool, optional): Send updates on the download
        status of issues over the websocket.
            Defaults to False.

    Returns:
        List[str]: The new filenames, only of files that have been converted.
    """
    planned_conversions: list[ProposedConversion] = []
    for proposed_convertion in _get_convertable_files(
        volume_id, issue_id, filepath_filter
    ):
        if proposed_convertion.target_format == "folder":
            resulting_files = proposed_convertion.perform_conversion()
            for filepath in resulting_files:
                sub_conversion = ConvertersManager.select_converter(filepath)
                if sub_conversion is not None:
                    planned_conversions.append(sub_conversion)

        else:
            planned_conversions.append(proposed_convertion)

    total_count = len(planned_conversions)
    if not total_count:
        return []

    # Commit changes because new connections are opened in the processes
    commit()
    result = []
    with PortablePool(max_processes=total_count) as pool:
        if update_websocket_progress:
            ws = WebSocket()
            ws.emit(TaskStatusEvent(f"Converted 0/{total_count}"))
            for idx, iter_result in enumerate(
                pool.imap_unordered(
                    lambda c: c.perform_conversion(), planned_conversions
                )
            ):
                result += iter_result
                ws.emit(TaskStatusEvent(f"Converted {idx + 1}/{total_count}"))

        else:
            result += chain.from_iterable(
                pool.map(lambda c: c.perform_conversion(), planned_conversions)
            )

    FilesDB.delete_filepaths(f.filepath for f in planned_conversions)
    scan_files(
        volume_id,
        filepath_filter=result,
        file_extra_info=file_extra_info,
        update_websocket=update_websocket_files,
    )

    return result
