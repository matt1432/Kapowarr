import re
from collections import Counter
from os.path import basename, dirname, join
from zipfile import ZipFile, ZipInfo

from backend.base.definitions import FileConstants
from backend.base.files import delete_file_folder, generate_archive_folder
from backend.base.logging import LOGGER
from backend.implementations.converters import cbr_to_cbz, cbz_to_cbr


def get_files_prefix(files: list[str]) -> str:
    # Extract prefix: everything up to the last occurrence of 1 or more digits
    prefixes = []

    for filename in files:
        match = list(re.finditer(r"\d+", basename(filename)))

        # Get positions relative to full path
        if match:
            match = list(re.finditer(r"[0-9]+", filename))

        if match:
            last = match[-1]
            prefixes.append(filename[: last.start()])
        else:
            prefixes.append(
                filename
            )  # If no digit sequence, use the whole string as prefix

    return Counter(prefixes).most_common(1)[0][0]


def find_outliers(files: list[ZipInfo]) -> list[str]:
    """
    From a list of files inside a zip file, get a list of files
    that do not follow the structure of the rest of the files.
    """
    filenames: list[str] = []

    for file in files:
        if not file.is_dir() and file.filename.endswith(
            FileConstants.IMAGE_EXTENSIONS
        ):
            filenames.append(file.filename)

    most_common_prefix = get_files_prefix(filenames)

    outliers: list[str] = []

    for filename in filenames:
        # We use startswith here because multi-pages images might not have the same prefix
        if not filename.startswith(most_common_prefix):
            outliers.append(filename)

    # If there are as many outliers as filenames, there are no outliers
    if len(outliers) == len(filenames) or len(outliers) == 0:
        no_numbers_outliers: list[str] = []

        for filename in filenames:
            if not re.search(r"\d+", basename(filename)):
                no_numbers_outliers.append(filename)

        return no_numbers_outliers

    return outliers


def get_ad_filenames(file: str) -> list[str]:
    """
    Gets all outliers that start with the letter 'x' or 'z'. Most ads
    will have one or more 'x' or 'z' at the start of the filename to
    show at the end of the book.
    """
    with ZipFile(file, "r") as zip:
        results: list[str] = []

        for outlier in find_outliers(zip.infolist()):
            if basename(outlier).lower()[0] in ["x", "z"]:
                results.append(outlier)

        return results


def remove_ads(file: str) -> None:
    """
    Removes scene ads that can sometimes show up at the end of comics.
    """
    is_rar = file.endswith(".cbr")

    if not file.endswith(".cbz") and not is_rar:
        return

    if is_rar:
        cbr_to_cbz(file)
        file = file.replace(".cbr", ".cbz")

    ads = get_ad_filenames(file)

    if len(ads) == 0:
        if is_rar:
            cbz_to_cbr(file)
        return

    archive_folder = generate_archive_folder(dirname(file), file)

    with ZipFile(file, "r") as zip:
        files = zip.namelist()
        zip.extractall(archive_folder)

    with ZipFile(file, "w") as zip:
        for f in files:
            if f not in ads:
                zip.write(filename=join(archive_folder, f), arcname=f)

    delete_file_folder(archive_folder)

    if is_rar:
        cbz_to_cbr(file)

    LOGGER.info(f"Removed ads: {ads}")
