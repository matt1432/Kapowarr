from asyncio import run
from glob import glob
from itertools import chain
from os.path import abspath, basename, dirname, isfile, splitext
from typing import Any

from backend.base.custom_exceptions import (
    InvalidKeyValue,
    VolumeAlreadyAdded,
)
from backend.base.definitions import (
    CVFileMapping,
    FileConstants,
    FilenameData,
    MonitorScheme,
    SpecialVersion,
)
from backend.base.file_extraction import extract_filename_data
from backend.base.files import (
    change_basefolder,
    common_folder,
    delete_empty_parent_folders,
    folder_is_inside_folder,
    list_files,
    rename_file,
)
from backend.base.helpers import DictKeyedDict, batched, force_range
from backend.base.logging import LOGGER
from backend.implementations.comicvine import ComicVine
from backend.implementations.naming import mass_rename
from backend.implementations.root_folders import RootFolders
from backend.implementations.volumes import Library, Volume, scan_files
from backend.internals.db import commit
from backend.internals.db_models import FilesDB


def propose_library_import(
    *,
    included_folders_str: str | None = None,
    excluded_folders_str: str | None = None,
    limit: int = 20,
    limit_parent_folder: bool = False,
    only_english: bool = True,
) -> list[dict]:
    """Get list of unimported files
    and their suggestion for a matching volume on CV.

    Args:
        included_folders (list[str], optional): Only scan the folders that
        match the given values. Can either be a list of folders or glob patterns.
            Defaults to an empty list.

        excluded_folders (list[str], optional): Only scan the folders that don't
        match the given values. Can either be a list of folders or glob patterns.
            Defaults to an empty list.

        limit (int, optional): The max amount of folders to scan.
            Defaults to 20.

        limit_parent_folder (bool, optional): Base the folder limit on
        parent folder, not folder. Useful if each issue has their own sub-folder.
            Defaults to False.

        only_english (bool, optional): Only match with english releases.
            Defaults to True.

    Raises:
        InvalidKeyValue: The file filter matches to folders outside
        the root folders.

    Returns:
        List[dict]: The list of files and their matches.
    """
    LOGGER.info("Loading library import")

    # Get all files in all root folders (with filter applied if given)
    root_folders = {abspath(r) for r in RootFolders().get_folder_list()}

    if included_folders_str and len(included_folders_str) != 0:
        included_folders = included_folders_str.split(",")

        scan_folders: set[str] = set().union(
            *(set(glob(folder, recursive=True)) for folder in included_folders)
        )

        for f in scan_folders:
            if not any(folder_is_inside_folder(r, f) for r in root_folders):
                raise InvalidKeyValue(
                    "included_folders_str", included_folders_str
                )
    else:
        scan_folders = root_folders.copy()

    scan_excluded_folders: set[str] = set()
    all_excluded_files: set[str] = set()

    if excluded_folders_str and len(excluded_folders_str) != 0:
        excluded_folders = excluded_folders_str.split(",")

        scan_excluded_folders = set().union(
            *(set(glob(folder, recursive=True)) for folder in excluded_folders)
        )

        try:
            all_excluded_files = set(
                chain.from_iterable(
                    list_files(f, FileConstants.CONTENT_EXTENSIONS)
                    for f in scan_excluded_folders
                )
            )

        except NotADirectoryError:
            raise InvalidKeyValue("excluded_folders_str", excluded_folders_str)
    try:
        all_files = set(
            chain.from_iterable(
                list_files(f, FileConstants.CONTENT_EXTENSIONS)
                for f in scan_folders
            )
        )

    except NotADirectoryError:
        raise InvalidKeyValue("included_folders_str", included_folders_str)

    # Get imported files
    imported_files = {f["filepath"] for f in FilesDB.fetch()}

    # Filter away imported files and apply limit
    folders = set()
    image_folders = set()
    # efd to files with that efd
    unimported_files = DictKeyedDict()
    for f in all_files:
        if f in imported_files or f in all_excluded_files:
            continue

        d = abspath(dirname(f))
        if d in root_folders:
            # File directly in root folder is not allowed
            continue

        efd = extract_filename_data(f, prefer_folder_year=True)
        del efd["issue_number"]  # pyright: ignore

        if (
            f.endswith(FileConstants.IMAGE_EXTENSIONS)
            and efd["special_version"] != SpecialVersion.COVER
        ):
            if d in image_folders:
                continue
            image_folders.add(d)
            d, f = dirname(d), d

        folders.add(dirname(d) if limit_parent_folder else d)

        if len(folders) > limit:
            break

        unimported_files.setdefault(efd, []).append(f)

    LOGGER.debug("File groupings: %s", unimported_files)

    # Find a match for the files on CV
    cv = ComicVine()
    result: list[dict[str, Any]] = []
    uf: list[FilenameData] = list(unimported_files.keys())
    uf.sort(
        key=lambda f: (
            f["series"],
            force_range(f["volume_number"] or 0)[0],
            f["year"] or 0,
        )
    )
    for batch_index, uf_batch in enumerate(batched(uf, 10)):
        group_to_cv = run(cv.filenames_to_cvs(uf_batch, only_english))
        result += [
            {
                "filepath": f,
                "file_title": (
                    splitext(basename(f))[0] if isfile(f) else basename(f)
                ),
                "cv": search_result,
                "group_number": batch_index * 10 + group_index,
            }
            for group_index, (group_data, search_result) in enumerate(
                group_to_cv.items()
            )
            for f in unimported_files[group_data]
        ]

    result.sort(key=lambda e: (e["group_number"], e["file_title"]))

    return result


def import_library(
    matches: list[CVFileMapping], rename_files: bool = False
) -> None:
    """Add volume to library and import linked files.

    Args:
        matches (List[CVFileMapping]): List of file mappings.

        rename_files (bool, optional): Trigger a rename after importing files.
            Defaults to False.
    """
    LOGGER.info("Starting library import")

    cvid_to_filepath: dict[int, list[str]] = {}
    for m in matches:
        cvid_to_filepath.setdefault(m["id"], []).append(m["filepath"])
    LOGGER.debug(f"id_to_filepath: {cvid_to_filepath}")

    root_folders = RootFolders().get_all()
    library = Library()

    for cv_id, files in cvid_to_filepath.items():
        # Find root folder that media is in
        for root_folder in root_folders:
            if folder_is_inside_folder(root_folder.folder, files[0]):
                break
        else:
            continue

        lcf = common_folder(files)

        try:
            volume_id = library.add(
                comicvine_id=cv_id,
                root_folder_id=root_folder.id,
                monitored=True,
                monitor_scheme=MonitorScheme.ALL,
                monitor_new_issues=True,
                volume_folder=lcf if not rename_files else None,
            )
            commit()

        except VolumeAlreadyAdded:
            # The volume is already added but the file is not matched to it
            # (it isn't because otherwise it wouldn't pop up in LI).
            # That would mean that the file is actually not
            # for that volume so skip.
            continue

        if rename_files:
            # Put files in volume folder
            vf = Volume(volume_id).vd.folder
            file_changes = change_basefolder(files, lcf, vf)
            for old, new in file_changes.items():
                if old != new:
                    rename_file(old, new)
                    delete_empty_parent_folders(
                        dirname(old), root_folder.folder
                    )

            new_files = list(file_changes.values())
            scan_files(volume_id)
            mass_rename(volume_id, filepath_filter=new_files)

        else:
            scan_files(volume_id, filepath_filter=files)

    return
