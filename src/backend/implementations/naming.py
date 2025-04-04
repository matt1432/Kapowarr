# -*- coding: utf-8 -*-

"""
The (re)naming of folders and media
"""

from __future__ import annotations

from os.path import abspath, basename, isdir, isfile, join, splitext
from re import compile
from string import Formatter
from sys import platform
from typing import Dict, List, Tuple, Type, Union

from backend.base.custom_exceptions import InvalidSettingValue
from backend.base.definitions import (BaseNamingKeys, FileConstants, IssueData,
                                      IssueNamingKeys, SpecialVersion,
                                      SVNamingKeys, VolumeData,
                                      full_sv_mapping, short_sv_mapping)
from backend.base.file_extraction import (cover_regex, extract_filename_data,
                                          page_regex, page_regex_2,
                                          process_issue_number)
from backend.base.files import (delete_empty_child_folders,
                                delete_empty_parent_folders, list_files,
                                make_filename_safe, rename_file)
from backend.base.helpers import (create_range, extract_year_from_date,
                                  filtered_iter)
from backend.base.logging import LOGGER
from backend.implementations.matching import (_match_title,
                                              file_importing_filter)
from backend.implementations.root_folders import RootFolders
from backend.implementations.volumes import Issue, Volume
from backend.internals.db_models import FilesDB
from backend.internals.server import WebSocket
from backend.internals.settings import Settings

remove_year_in_image_regex = compile(r'(?:19|20)\d{2}')


# =====================
# region Name generation
# =====================
def _get_volume_naming_keys(
    volume: Union[int, VolumeData],
    _special_version: Union[SpecialVersion, None] = None
) -> SVNamingKeys:
    """Generate the values of the naming keys for a volume.

    Args:
        volume (Union[int, VolumeData]): The ID of the volume to fetch the data
        for or manually supplied volume data to work with.
        _special_version (Union[SpecialVersion, None], optional): Override the
        Special Version used.
            Defaults to None.

    Returns:
        SVNamingKeys: The values of the naming keys for a volume.
    """
    if isinstance(volume, int):
        volume_data = Volume(volume, check_existence=True).get_data()
    else:
        volume_data = volume

    if _special_version is not None:
        volume_data.__dict__["special_version"] = _special_version

    settings = Settings().get_settings()
    long_special_version = settings.long_special_version
    volume_padding = settings.volume_padding
    series_name = (
        volume_data.title
        .replace('/', '')
        .replace(r'\\', '')
    )

    for prefix in ('The ', 'A '):
        if series_name.startswith(prefix):
            clean_title = series_name[len(prefix):] + ", " + prefix.strip()
            break
    else:
        clean_title = series_name

    sv_mapping = full_sv_mapping if long_special_version else short_sv_mapping

    return SVNamingKeys(
        series_name=series_name,
        clean_series_name=clean_title,
        volume_number=str(volume_data.volume_number).zfill(volume_padding),
        comicvine_id=volume_data.comicvine_id,
        year=volume_data.year,
        publisher=volume_data.publisher,
        special_version=sv_mapping.get(volume_data.special_version)
    )


def _get_issue_naming_keys(
    volume: Union[int, VolumeData],
    issue: Union[int, IssueData]
) -> IssueNamingKeys:
    """Generate the values of the naming keys for an issue.

    Args:
        volume (Union[int, VolumeData]): The ID of the volume to fetch the data
        for or manually supplied volume data to work with.
        issue (Union[int, IssueData]): The ID of the issue to fetch the data
        for or manually supplied issue data to work with.

    Returns:
        IssueNamingKeys: The values of the naming keys for an issue.
    """
    issue_padding = Settings().sv.issue_padding

    if isinstance(issue, int):
        issue_data = Issue(
            issue, check_existence=True
        ).get_data()
    else:
        issue_data = issue

    return IssueNamingKeys(
        **_get_volume_naming_keys(volume).__dict__,
        issue_comicvine_id=issue_data.comicvine_id,
        issue_number=(
            str(issue_data.issue_number or '').zfill(issue_padding)
            or None
        ),
        issue_title=(
            (issue_data.title or '')
            .replace('/', '')
            .replace(r'\\', '')
            or None
        ),
        issue_release_date=issue_data.date,
        issue_release_year=extract_year_from_date(issue_data.date)
    )


def generate_volume_folder_name(
    volume: Union[int, VolumeData]
) -> str:
    """Generate a volume folder name based on the format string.

    Args:
        volume (Union[int, VolumeData]): The ID of the volume to generate the
        name for or manually supplied volume data to generate a name with.

    Returns:
        str: The volume folder name.
    """
    formatting_data = _get_volume_naming_keys(volume)
    format = Settings().sv.volume_folder_naming

    name = format.format_map({
        k: v if v is not None else 'Unknown'
        for k, v in formatting_data.__dict__.items()
    })
    save_name = make_filename_safe(name)
    return save_name


def generate_volume_folder_path(
    root_folder: str,
    volume: Union[int, str]
) -> str:
    """Generate an absolute path to a volume folder.

    Args:
        root_folder (str): The root folder that the volume is in.
        volume (Union[int, str]): Either the ID of the volume when the folder
        name needs to be generated, or the path of the custom volume folder.

    Returns:
        str: The absolute path to the volume folder, allowing custom folders.
    """
    if isinstance(volume, str):
        vf = volume
    else:
        vf = generate_volume_folder_name(volume)

    return make_filename_safe(abspath(join(root_folder, vf)))


def generate_issue_name(
    volume_id: int,
    special_version: SpecialVersion,
    calculated_issue_number: Union[float, Tuple[float, float], None]
) -> str:
    """Generate an issue file name based on the format string for the issue
    type.

    Args:
        volume_id (int): The ID of the volume that the file is for.
        special_version (SpecialVersion): The Special Version of the volume.
        calculated_issue_number (Union[float, Tuple[float, float], None]):
        The issue (or issue range) that the file covers. Give volume number
        here in case of VAI.

    Raises:
        IssueNotFound: No issue found with the given issue number.

    Returns:
        str: The issue file name.
    """
    normal_filename = False
    sv = Settings().sv

    if special_version in (
        SpecialVersion.TPB,
        SpecialVersion.ONE_SHOT,
        SpecialVersion.HARD_COVER
    ):
        # Iron-Man Volume 2 One-Shot
        formatting_data = _get_volume_naming_keys(volume_id)
        format = sv.file_naming_special_version

    elif special_version == SpecialVersion.VOLUME_AS_ISSUE:
        # Iron-Man Volume 1 - 3
        issue = Issue.from_volume_and_calc_number(
            volume_id, create_range(calculated_issue_number)[0] # type: ignore
        )
        formatting_data = _get_issue_naming_keys(volume_id, issue.id)
        format = sv.file_naming_vai

    elif special_version != SpecialVersion.NORMAL:
        # Iron-Man Volume 2 Cover
        formatting_data = _get_volume_naming_keys(
            volume_id,
            _special_version=special_version
        )
        format = sv.file_naming_special_version

    else:
        # Iron-Man Volume 1 Issue 2 - 3
        normal_filename = True
        issue = Issue.from_volume_and_calc_number(
            volume_id,
            create_range(calculated_issue_number)[0] # type: ignore
        )
        formatting_data = _get_issue_naming_keys(volume_id, issue.id)

        if formatting_data.issue_title is None:
            format = sv.file_naming_empty
        else:
            format = sv.file_naming

    if (
        isinstance(calculated_issue_number, tuple)
        and isinstance(formatting_data, IssueNamingKeys)
    ):
        issue_number_end = Issue.from_volume_and_calc_number(
            volume_id,
            calculated_issue_number[1]
        ).get_data().issue_number
        formatting_data.issue_number = (
            str(formatting_data.issue_number)
            .zfill(sv.issue_padding)
            + ' - ' +
            str(issue_number_end)
            .zfill(sv.issue_padding)
        )

    name = format.format_map({
        k: v if v is not None else 'Unknown'
        for k, v in formatting_data.__dict__.items()
    })
    save_name = make_filename_safe(name)

    if (
        normal_filename
        and format == sv.file_naming
        and extract_filename_data(save_name)['issue_number']
            != calculated_issue_number
    ):
        # When applying the EFD algorithm to the generated filename, we don't
        # get back the same issue number(s) as that we originally made the
        # filename for. This probably means that the title of the issue is
        # messing up the algorithm. E.g. the title of issue 4 is "Book 1",
        # then EFD might think the file is for issue 1 instead of 4. Try a name
        # without the title and see if that fixes it. If so, use it. If not,
        # then give up and just use the original name.
        titleless_name = sv.file_naming_empty.format_map({
            k: v if v is not None else 'Unknown'
            for k, v in formatting_data.__dict__.items()
        })
        titleless_save_name = make_filename_safe(titleless_name)
        if (
            extract_filename_data(titleless_save_name)['issue_number']
                == calculated_issue_number
        ):
            save_name = titleless_save_name

    return save_name


def generate_image_name(
    filename: str
) -> str:
    """Generate an image file name based on what the current filename suggests
    is the cover or page covered.

    Args:
        filename (str): The current filename of the image file.

    Returns:
        str: The image file name.
    """
    file_body = remove_year_in_image_regex.sub(
        '',
        splitext(basename(filename))[0]
    )

    cover_result = cover_regex.search(file_body)
    if cover_result:
        return f'Cover {cover_result.groups("")[0]}'.strip()

    page_result = page_regex.search(file_body)
    if page_result:
        return next(filter(
            bool,
            page_result.groups()
        ))

    page_result = page_regex_2.findall(file_body)
    if page_result:
        return page_result[-1]

    return '1'


# =====================
# region Checking formats
# =====================
NAMING_MAPPING: Dict[str, Type[BaseNamingKeys]] = {
    'volume_folder_naming': BaseNamingKeys,
    'file_naming': IssueNamingKeys,
    'file_naming_empty': IssueNamingKeys,
    'file_naming_special_version': SVNamingKeys,
    'file_naming_vai': IssueNamingKeys
}


def check_format(format: str, type: str) -> bool:
    """Check if a format string is valid.

    Args:
        format (str): The format string to check.
        type (str): What type of format string it is, specified by their
        settings key. E.g. 'file_naming'.

    Returns:
        bool: Whether the format is allowed.
    """
    if platform.startswith('win32'):
        disallowed_sep = '/'
    else:
        disallowed_sep = '\\'

    if disallowed_sep in format:
        return False

    keys = [
        fn
        for _, fn, _, _ in Formatter().parse(format)
        if fn is not None
    ]

    naming_keys = NAMING_MAPPING[type]
    for format_key in keys:
        if format_key not in naming_keys.__dataclass_fields__:
            return False

    return True


def check_mock_filename(
    volume_folder_naming: Union[str, None],
    file_naming: Union[str, None],
    file_naming_empty: Union[str, None],
    file_naming_special_version: Union[str, None],
    file_naming_vai: Union[str, None]
) -> None:
    """Check if the supplied naming formats are supported by Kapowarr. This is
    checked by creating a filename using the format, and seeing if it matches
    to a fake volume and issue. If it does not match, then the filename must be
    insufficient.

    Args:
        volume_folder_naming (Union[str, None]): The new naming format for the
        volume folder, or `None` if the current one should be used.

        file_naming (Union[str, None]): The new naming format for a standard
        file, or `None` if the current one should be used.

        file_naming_empty (Union[str, None]): The new naming format for an issue
        without title, or `None` if the current one should be used.

        file_naming_special_version (Union[str, None]): The new naming format
        for a Special Version, or `None` if the current one should be used.

        file_naming_vai (Union[str, None]): The new naming format for a VAI,
        or `None` if the current one should be used.

    Raises:
        InvalidSettingValue: One of the formats is insufficient.
    """
    naming_mocks = {
        "file_naming_special_version": [
            (
                VolumeData(
                    id=0,
                    comicvine_id=123,
                    title="Spider-Man",
                    alt_title="Spiderman",
                    year=2023,
                    publisher="Marvel",
                    volume_number=2,
                    description="",
                    site_url="",
                    monitored=True,
                    monitor_new_issues=True,
                    root_folder=1,
                    folder="",
                    custom_folder=False,
                    special_version=SpecialVersion.ONE_SHOT,
                    special_version_locked=False,
                    last_cv_fetch=0
                ),
                [
                    IssueData(
                        id=0,
                        volume_id=0,
                        comicvine_id=456,
                        issue_number="1",
                        calculated_issue_number=create_range(
                            process_issue_number("1") or 0.0
                        )[0],
                        title="One Shot",
                        date="2023-03-04",
                        description="",
                        monitored=True,
                        files=[]
                    )
                ]
            ),
            (
                VolumeData(
                    id=0,
                    comicvine_id=123,
                    title="Spider-Man",
                    alt_title="Spiderman",
                    year=2023,
                    publisher="Marvel",
                    volume_number=2,
                    description="",
                    site_url="",
                    monitored=True,
                    monitor_new_issues=True,
                    root_folder=1,
                    folder="",
                    custom_folder=False,
                    special_version=SpecialVersion.TPB,
                    special_version_locked=False,
                    last_cv_fetch=0
                ),
                [
                    IssueData(
                        id=0,
                        volume_id=0,
                        comicvine_id=456,
                        issue_number="1",
                        calculated_issue_number=create_range(
                            process_issue_number("1") or 0.0
                        )[0],
                        title="",
                        date="2023-03-04",
                        description="",
                        monitored=True,
                        files=[]
                    )
                ]
            )
        ],
        "file_naming": [
            (
                VolumeData(
                    id=0,
                    comicvine_id=123,
                    title="Spider-Man",
                    alt_title="Spiderman",
                    year=2023,
                    publisher="Marvel",
                    volume_number=2,
                    description="",
                    site_url="",
                    monitored=True,
                    monitor_new_issues=True,
                    root_folder=1,
                    folder="",
                    custom_folder=False,
                    special_version=SpecialVersion.NORMAL,
                    special_version_locked=False,
                    last_cv_fetch=0
                ),
                [
                    IssueData(
                        id=0,
                        volume_id=0,
                        comicvine_id=456,
                        issue_number="3b",
                        calculated_issue_number=create_range(
                            process_issue_number("3b") or 0.0
                        )[0],
                        title="",
                        date="2023-03-04",
                        description="",
                        monitored=True,
                        files=[]
                    )
                ]
            )
        ],
        "file_naming_vai": [
            (
                VolumeData(
                    id=0,
                    comicvine_id=123,
                    title="Spider-Man",
                    alt_title="Spiderman",
                    year=2023,
                    publisher="Marvel",
                    volume_number=2,
                    description="",
                    site_url="",
                    monitored=True,
                    monitor_new_issues=True,
                    root_folder=1,
                    folder="",
                    custom_folder=False,
                    special_version=SpecialVersion.VOLUME_AS_ISSUE,
                    special_version_locked=False,
                    last_cv_fetch=0
                ),
                [
                    IssueData(
                        id=0,
                        volume_id=0,
                        comicvine_id=456,
                        issue_number="8",
                        calculated_issue_number=create_range(
                            process_issue_number("8") or 0.0
                        )[0],
                        title="",
                        date="2023-03-04",
                        description="",
                        monitored=True,
                        files=[]
                    )
                ]
            )
        ]
    }
    naming_mocks['file_naming_empty'] = naming_mocks['file_naming']

    settings = Settings().get_settings()
    vf_naming = volume_folder_naming or settings.volume_folder_naming
    namings = {
        'file_naming': file_naming or settings.file_naming,
        'file_naming_empty': file_naming_empty or settings.file_naming_empty,
        'file_naming_special_version': file_naming_special_version or settings.file_naming_special_version,
        'file_naming_vai': file_naming_vai or settings.file_naming_vai}

    for key, value in namings.items():
        filepath = join(vf_naming, value)
        for volume_mock, issue_mock in naming_mocks[key]:
            if key == 'file_naming_special_version':
                formatting_data = _get_volume_naming_keys(volume_mock)
            else:
                formatting_data = _get_issue_naming_keys(
                    volume_mock, issue_mock[0]
                )

            name = filepath.format_map({
                k: v if v is not None else 'Unknown'
                for k, v in formatting_data.__dict__.items()
            })
            save_name = make_filename_safe(name)

            number_to_year: Dict[float, Union[int, None]] = {
                i.calculated_issue_number: extract_year_from_date(i.date)
                for i in issue_mock
            }
            efd = extract_filename_data(save_name)
            if not (
                file_importing_filter(
                    efd,
                    volume_mock,
                    issue_mock,
                    number_to_year
                )
                and _match_title(efd['series'], volume_mock.title)
                and (
                    # Special version doesn't need issue matching
                    key == 'file_naming_special_version'
                    or (
                        # Issue number must match
                        key in (
                            'file_naming', 'file_naming_empty',
                            'file_naming_vai'
                        )
                        and efd["issue_number"] == issue_mock[0].calculated_issue_number
                    )
                    or (
                        # VAI name has issue number labeled as volume number
                        key == 'file_naming_vai'
                        and efd["volume_number"] == issue_mock[0].calculated_issue_number
                    )
                )
            ):
                raise InvalidSettingValue(key, value)
    return


# =====================
# region Renaming
# =====================
def same_name_indexing(
    volume_folder: str,
    planned_renames: Dict[str, str]
) -> Dict[str, str]:
    """Add a number at the end the filenames if the suggested filename already
    exists.

    Args:
        volume_folder (str): The volume folder that the files will be in.
        planned_renames (Dict[str, str]): The currently planned renames (key
        is before, value is after).

    Returns:
        Dict[str, str]: The planned renamed, now updated with numbers i.c.o.
        duplicate filenames.
    """
    if not isdir(volume_folder):
        return planned_renames

    final_names = set(list_files(volume_folder))
    for before, after in planned_renames.items():

        new_after = after
        index = 1
        while before != new_after and new_after in final_names:
            new_after = splitext(after)[0] + f' ({index})' + splitext(after)[1]
            index += 1

        final_names.add(new_after)
        planned_renames[before] = new_after

    return {
        k: v
        for k, v in planned_renames.items()
        if k != v
    }


def preview_mass_rename(
    volume_id: int,
    issue_id: Union[int, None] = None,
    filepath_filter: Union[List[str], None] = None
) -> Tuple[Dict[str, str], Union[str, None]]:
    """Determine what the new filenames would be, if they aren't already
    following the format.

    Args:
        volume_id (int): The ID of the volume for which to check the renaming.

        issue_id (Union[int, None], optional): The ID of the issue for which to
        check the renaming.
            Defaults to None.

        filepath_filter (Union[List[str], None], optional): Only process files
        that are in the list.
            Defaults to None.

    Returns:
        Tuple[Dict[str, str], Union[str, None]]: The renaming proposals where
        the key is the "before" and the value is the "after", and the new volume
        folder if it is not the same as the current folder. Otherwise, it's
        `None`.
    """
    result = {}
    volume = Volume(volume_id)
    volume_data = volume.get_data()
    volume_folder = volume_data.folder

    files = tuple(filtered_iter(
        sorted(
            f["filepath"] for f in (
                volume.get_all_files()
                if not issue_id else
                volume.get_issue(issue_id).get_files()
            )
        ),
        set(filepath_filter or [])
    ))

    if not issue_id:
        if not files:
            return result, None

        if not volume_data.custom_folder:
            root_folder = RootFolders()[volume_data.root_folder]
            volume_folder = generate_volume_folder_path(
                root_folder,
                volume_id
            )

    for file in files:
        if not isfile(file):
            continue

        LOGGER.debug(f'Renaming: original filename: {file}')

        issues = FilesDB.issues_covered(file)
        if len(issues) > 1:
            gen_filename_body = generate_issue_name(
                volume_id,
                volume_data.special_version,
                (issues[0], issues[-1]),
            )

        elif issues:
            gen_filename_body = generate_issue_name(
                volume_id,
                volume_data.special_version,
                issues[0],
            )

            if basename(file.lower()) in FileConstants.METADATA_FILES:
                gen_filename_body += ' ' + splitext(basename(file))[0]

        elif file.endswith(FileConstants.IMAGE_EXTENSIONS):
            # Cover
            gen_filename_body = generate_issue_name(
                volume_id,
                SpecialVersion.COVER,
                calculated_issue_number=None
            )

        else:
            # Metadata
            gen_filename_body = splitext(basename(file))[0]

        if issues and file.endswith(FileConstants.IMAGE_EXTENSIONS):
            # Image file is page of issue, so put it in it's own
            # folder together with the other images.
            gen_filename_body = join(
                gen_filename_body,
                generate_image_name(file)
            )

        suggested_name = join(
            volume_folder,
            gen_filename_body + splitext(file)[1].lower()
        )

        LOGGER.debug(f'Renaming: suggested filename: {suggested_name}')
        if file != suggested_name:
            LOGGER.debug(f'Renaming: added rename')
            result[file] = suggested_name

    result = same_name_indexing(volume_folder, result)

    if volume_folder != volume.get_data().folder:
        return result, volume_folder
    else:
        return result, None


def mass_rename(
    volume_id: int,
    issue_id: Union[int, None] = None,
    filepath_filter: Union[List[str], None] = None,
    update_websocket: bool = False
) -> List[str]:
    """Rename files so that they follow the naming formats.

    Args:
        volume_id (int): The ID of the volume for which to rename.

        issue_id (Union[int, None], optional): The ID of the issue for which
        to rename.
            Defaults to None.

        filepath_filter (Union[List[str], None], optional): Only rename files
        that are in the list.
            Defaults to None.

        update_websocket (bool, optional): Send task progress updates over
        the websocket.
            Defaults to False.

    Returns:
        List[str]: The new filenames, only of files that have been be renamed.
    """
    renames, new_volume_folder = preview_mass_rename(
        volume_id, issue_id,
        filepath_filter
    )
    if not renames and not new_volume_folder:
        return []

    volume = Volume(volume_id)
    volume_data = volume.get_data()
    root_folder = RootFolders()[volume_data.root_folder]

    if new_volume_folder:
        volume['folder'] = new_volume_folder

    if update_websocket:
        ws = WebSocket()
        total_renames = len(renames)
        for idx, (before, after) in enumerate(renames.items()):
            ws.update_task_status(
                message=f'Renaming file {idx+1}/{total_renames}'
            )
            rename_file(before, after)

    else:
        for before, after in renames.items():
            rename_file(before, after)

    FilesDB.update_filepaths(*zip(*renames.items()))

    if renames:
        delete_empty_child_folders(volume_data.folder)
        delete_empty_parent_folders(volume_data.folder, root_folder)

    LOGGER.info(
        f'Renamed volume {volume_id} {f"issue {issue_id}" if issue_id else ""}'
    )
    return list(renames.values())
