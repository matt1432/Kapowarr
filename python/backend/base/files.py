"""
Handling folders, files and filenames.
"""

from collections import deque
from collections.abc import Iterable, Sequence
from os import PathLike, listdir, makedirs, remove, scandir
from os.path import (
    abspath,
    basename,
    commonpath,
    dirname,
    isdir,
    isfile,
    join,
    relpath,
    samefile,
    sep,
    splitext,
)
from re import compile
from shutil import copy2, copytree, move, rmtree

from backend.base.definitions import CharConstants, Constants, FileConstants
from backend.base.helpers import check_filter, force_suffix
from backend.base.logging import LOGGER

StrPath = str | PathLike[str]

filepath_cleaner = compile(r"(<|>|(?<!^\w):|\"|\||\?|\*|\x00|(?:\s|\.)+(?=$|\\|/))")
smart_filepath_cleaner_compact = compile(r"(\b[<>:]\b)")
smart_filepath_cleaner_spaced = compile(r"(\b\s[<>]\s\b|\b:\s\b)")
smart_filestring_cleaner_compact = compile(r"((?:\b|^)/(?:\b|$))")


# region Conversion
def dirname_times(path: str, amount: int = 1) -> str:
    """Apply `os.path.dirname` to `path` for `amount` times.

    Args:
        path (str): The path to apply to.
        amount (int, optional): The amount of times to apply dirname.
            Defaults to 1.

    Returns:
        str: The resulting path.
    """
    for _ in range(0, amount):
        path = dirname(path)
    return path


def folder_path(*folders: str) -> str:
    """Turn filepaths relative to the project folder into absolute paths.

    Returns:
        str: The absolute filepath.
    """
    return join(dirname_times(abspath(__file__), 3), *folders)


def folder_is_inside_folder(base_folder: str, folder: str) -> bool:
    """Check if folder is inside base_folder.

    Args:
        base_folder (str): The base folder to check against.
        folder (str): The folder that should be inside base_folder.

    Returns:
        bool: Whether or not folder is in base_folder.
    """
    return (force_suffix(abspath(folder))).startswith(
        force_suffix(abspath(base_folder))
    )


def find_common_folder(files: Sequence[str]) -> str:
    """Find the deepest folder that is shared between the files.

    Args:
        files (Sequence[str]): The list of files to find the deepest common folder
        for.

    Returns:
        str: The path of the deepest common folder.
    """
    if len(files) == 1:
        return dirname(files[0])

    return commonpath(files)


def uppercase_drive_letter(path: str) -> str:
    """Return the input, but if it's a Windows path that starts with a drive
    letter, then return the path with the drive letter uppercase.

    Args:
        path (str): The input path, possibly a windows path with a drive letter.

    Returns:
        str: The input path, but with an upper case Windows drive letter if
        a Windows drive letter is present.
    """
    if (
        len(path) >= 4
        and (path[1:3] == ":\\" or path[1:3] == ":/")
        and path[0].lower() in CharConstants.ALPHABET
    ):
        path = path[0].upper() + path[1:]

    return path


def set_detected_extension(filepath: str) -> str:
    """Find the archive type of a file based on its actual mimetype (via magic
    bytes) and return the filepath with the correct extension. If the file
    is not an archive or the archive is not recognised, the original
    filepath is returned.

    This function is not very fast because it has to read the first few bytes
    of the file. So only use when really necessary.

    Args:
        filepath (str): The filepath to check and possibly change the extension of.

    Returns:
        str: The filepath with the correct extension based on the archive type.
    """
    max_len = max(len(sig) for sig in FileConstants.ARCHIVE_MAGIC_BYTES)

    with open(filepath, "rb") as f:
        file_start = f.read(max_len)
        for sig, ext in FileConstants.ARCHIVE_MAGIC_BYTES.items():
            if file_start.startswith(sig):
                break
        else:
            return filepath

    # Found archive type
    file_parts = splitext(filepath)
    current_extension = file_parts[1].lower().lstrip(".")
    if current_extension == ext:
        # Already has the correct extension
        return filepath

    if current_extension in FileConstants.CB_TO_ARCHIVE_EXTENSIONS:
        # Current file uses cb* extension, so find cb* version of proper
        # extension
        for cb_ext, normal_ext in FileConstants.CB_TO_ARCHIVE_EXTENSIONS.items():
            if ext == normal_ext:
                ext = cb_ext
                break
        else:
            return filepath

    return file_parts[0] + "." + ext


def clean_filepath_simple(filepath: str) -> str:
    """Clean a filepath by removing illegal characters. This makes it safe for
    a use in a filesystem.

    Args:
        filepath (str): The filepath to be cleaned.

    Returns:
        str: The cleaned filepath.
    """
    safe_filepath = filepath_cleaner.sub("", filepath)
    return safe_filepath


def clean_filepath_smartly(filepath: str) -> str:
    """Clean a filepath by replacing illegal characters smartly. Either remove
    the character, replace it with a dash or dash with spaces around it. This
    makes it safe for a use in a filesystem.

    Args:
        filepath (str): The filepath to be cleaned.

    Returns:
        str: The cleaned filepath.
    """
    save_filepath = smart_filepath_cleaner_compact.sub("-", filepath)
    save_filepath = smart_filepath_cleaner_spaced.sub(" - ", save_filepath)
    save_filepath = clean_filepath_simple(save_filepath)
    return save_filepath


def clean_filestring_simple(filestring: str) -> str:
    """Clean a part of a filename (so no path seperators) by removing illegal
    characters. This makes it safe for a use in a filesystem.

    Args:
        filestring (str): The string to clean.

    Returns:
        str: The cleaned string.
    """
    return clean_filepath_simple(filestring.replace("/", "").replace("\\", ""))


def clean_filestring_smartly(filestring: str) -> str:
    """Clean a part of a filename (so no path seperators) by replacing illegal
    characters smartly. Either remove the character, replace it with a dash or
    dash with spaces around it. This makes it safe for a use in a filesystem.

    Args:
        filestring (str): The string to clean.

    Returns:
        str: The cleaned string.
    """
    save_filepath = smart_filestring_cleaner_compact.sub("-", filestring)
    save_filepath = save_filepath.replace(" / ", " - ")
    save_filepath = clean_filepath_smartly(save_filepath)
    return save_filepath


def list_files(folder: str, ext: Iterable[str] = []) -> list[str]:
    """List all files in a folder recursively with absolute paths. Hidden files
    (files starting with `.`) are ignored.

    Args:
        folder (str): The base folder to search through.

        ext (Iterable[str], optional): File extensions to only include.
        Dot-prefix not necessary.
            Defaults to [].

    Returns:
        List[str]: The paths of the files in the folder.
    """
    files: deque[str] = deque()

    def _list_files(folder: str, ext: set[str] = set()) -> None:
        """Internal function to add all files in a folder to the files list.

        Args:
            folder (str): The base folder to search through.
            ext (Set[str], optional): A set of lowercase, dot-prefixed,
            extensions to filter for or empty for no filter. Defaults to set().
        """
        for f in scandir(folder):
            if f.is_dir():
                _list_files(f.path, ext)

            elif (
                f.is_file()
                and not f.name.startswith(".")
                and check_filter(splitext(f.name)[1].lower(), ext)
            ):
                files.append(f.path)

    ext = {"." + e.lower().lstrip(".") for e in ext}
    _list_files(folder, ext)
    return list(files)


def propose_basefolder_change(
    files: Iterable[str], current_base_folder: str, desired_base_folder: str
) -> dict[str, str]:
    """
    Propose new filenames with a different base folder for a list of files.
    E.g. /current/base/folder/file.ext -> /desired_base_folder/file.ext

    Args:
        files (Iterable[str]): Iterable of files to change base folder for.
        current_base_folder (str): Current base folder, to replace.
        desired_base_folder (str): Desired base folder, to replace with.

    Returns:
        Dict[str, str]: Key is old filename, value is new filename.
    """
    file_changes = {
        f: join(desired_base_folder, relpath(f, current_base_folder)) for f in files
    }

    return file_changes


def generate_archive_folder(volume_folder: str, archive_file: str) -> str:
    """Generate a folder in which the given archive file can be extracted.

    Args:
        volume_folder (str): The volume folder that the archive file is in.
        archive_file (str): The filepath of the archive file itself.

    Returns:
        str: The folder in which the archive file can be extracted.
    """
    return join(
        volume_folder,
        Constants.ARCHIVE_EXTRACT_FOLDER
        + "_"
        + splitext("_".join(relpath(archive_file, volume_folder).split(sep)))[0],
    )


# region Creation
def create_folder(folder: str) -> None:
    """Create a folder

    Args:
        folder (str): The path to the folder to create.
    """
    makedirs(folder, exist_ok=True)
    return


# region Moving
def __copy2[T: StrPath](
    src: StrPath, dst: T, *, follow_symlinks: bool = True
) -> T | str:
    try:
        return copy2(src, dst, follow_symlinks=follow_symlinks)

    except PermissionError as pe:
        if pe.errno == 1:
            # Issue 117
            # NFS file system doesn't allow/support chmod.
            # This is done after the file is already copied. So just accept that
            # it isn't possible to change the permissions. Continue like normal.
            return dst

        raise

    except OSError as oe:
        if oe.errno == 524:
            # Issue 229
            # NFS file system doesn't allow/support setting extended attributes.
            # This is done after the file is already copied. So just accept that
            # it isn't possible to set them. Continue like normal.
            return dst

        raise


def rename_file(before: str, after: str) -> None:
    """Rename a file, taking care of new folder locations and
    the possible complications with files on OS'es.

    Args:
        before (str): The current filepath of the file.
        after (str): The new desired filepath of the file.
    """
    if folder_is_inside_folder(before, after):
        # Cannot move folder into itself
        return

    LOGGER.debug(f"Renaming file {before} to {after}")

    create_folder(dirname(after))

    # Move file into folder
    move(before, after, copy_function=__copy2)

    return


def copy_directory(source: str, target: str) -> None:
    """Copy a directory.

    Args:
        source (str): The path to the source directory.
        target (str): The path to where the directory should be copied.
    """
    copytree(source, target, copy_function=__copy2)
    return


# region Deletion
def delete_file_folder(path: str) -> None:
    """Delete a file or folder. In the case of a folder, it is deleted recursively.

    Args:
        path (str): The path to the file or folder.
    """
    if isfile(path):
        remove(path)

    elif isdir(path):
        rmtree(path, ignore_errors=True)

    return


def delete_empty_parent_folders(top_folder: str, root_folder: str) -> None:
    """Delete parent folders that are empty until we reach a folder with content
    or the root folder. Take notice of the difference between this function and
    `delete_empty_child_folders()`.

    For example, with the following file structure, and
    `top_folder="/a/b1/c1/d1", root_folder="/a"`, the folder `/a/b1/c1` is
    deleted.
    ```
    /a/b1/c1/d1/
    /a/b1/c2/d2.txt
    ```

    Args:
        top_folder (str): The folder to start deleting from.
        root_folder (str): The root folder to stop at in case we reach it.
    """
    if top_folder == root_folder:
        return

    LOGGER.debug(f"Deleting empty parent folders from {top_folder} until {root_folder}")

    if not folder_is_inside_folder(root_folder, top_folder):
        LOGGER.error(f"The folder {top_folder} is not in {root_folder}")
        return

    if isfile(top_folder):
        top_folder = dirname(top_folder)

    parent_folder = top_folder
    child_folder = None

    while parent_folder:
        if isdir(parent_folder):
            if samefile(parent_folder, root_folder):
                break

            if listdir(parent_folder) not in ([], [child_folder]):
                # Folder has content and it's not only the empty child
                break

        child_folder = basename(parent_folder)
        parent_folder = dirname(parent_folder)

    if child_folder:
        lowest_empty_folder = join(parent_folder, child_folder)
        LOGGER.debug(f"Deleting folder and children: {lowest_empty_folder}")
        delete_file_folder(lowest_empty_folder)

    return


def delete_empty_child_folders(base_folder: str) -> None:
    """Delete child folders that don't (indirectly) contain any files. Take
    notice of the difference between this function and
    `delete_empty_parent_folders()`.

    For example, with the following file structure, and `base_folder="/a"`,
    the folders `/a/b1` and `/a/b2/c2` are deleted because they don't contain
    any files.
    ```
    /a/b1/c1/d1/
    /a/b1/c1/d2/
    /a/b2/c2/
    /a/b2/c3.txt
    /a/b3.txt
    ```

    Args:
        base_folder (str): The base folder to remove children of.
    """
    LOGGER.debug(f"Deleting empty child folders from {base_folder}")

    if isfile(base_folder):
        base_folder = dirname(base_folder)

    resulting_folders: list[str] = []

    def _decf(
        folder: str, resulting_folders: list[str], _first_call: bool = True
    ) -> bool:
        folders: list[str] = []
        contains_files: bool = False

        for f in scandir(folder):
            if f.is_dir():
                folders.append(f.path)
            elif f.is_file():
                contains_files = True

        if not (contains_files or folders):
            # Folder is empty
            return True

        sub_folder_results = {f: _decf(f, resulting_folders, False) for f in folders}

        if not contains_files and all(sub_folder_results.values()):
            # Folder only contains (indirectly) empty folders
            if _first_call:
                resulting_folders.extend(sub_folder_results.keys())
            return True

        resulting_folders.extend((k for k, v in sub_folder_results.items() if v))

        return False

    _decf(base_folder, resulting_folders)

    for f in resulting_folders:
        LOGGER.debug(f"Deleting folder and children: {f}")
        delete_file_folder(f)

    return
