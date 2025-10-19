from io import BytesIO
from os.path import basename, dirname, exists, join
from zipfile import ZipFile

from PIL import Image

from backend.base.definitions import Constants, ThumbnailData
from backend.base.files import (
    create_folder,
    delete_file_folder,
    folder_path,
    generate_archive_folder,
    list_files,
)
from backend.implementations.ad_removal import get_files_prefix
from backend.implementations.converters import CBRtoCBZ, CBZtoCBR
from backend.implementations.volumes import Volume
from backend.internals.db_models import FilesDB


def extract_files(file: str) -> list[str]:
    volume_id = FilesDB.volume_of_file(file)

    if not volume_id:
        # File not matched to volume
        return [file]

    volume_folder = Volume(volume_id).vd.folder
    archive_folder = generate_archive_folder(volume_folder, file)

    is_rar = file.endswith(".cbr")
    if is_rar:
        CBRtoCBZ.convert(file)
        file = file.replace(".cbr", ".cbz")

    with ZipFile(file, "r") as zip:
        zip.extractall(archive_folder)

    resulting_files = list_files(archive_folder)

    if is_rar:
        CBZtoCBR.convert(file)

    return resulting_files


def _get_thumbnails_folder(
    issue_id: int,
    file_path: str,
) -> str:
    # Place the thumbnails at the same place as the Kapowarr db
    from backend.internals.settings import about_data

    volume_id = FilesDB.volume_of_file(file_path)
    file_id = FilesDB.fetch(filepath=file_path)[0]["id"]

    return join(
        dirname(about_data["database_location"])
        or folder_path(*Constants.DB_FOLDER),
        Constants.THUMBNAILS_FOLDER_NAME,
        str(volume_id),
        str(issue_id),
        str(file_id),
    )


def _generate_thumbnail(file_path: str, folder: str) -> str:
    img = Image.open(file_path)

    # We want to set the height of each page to 600
    new_size_ratio = 600.0 / float(img.size[1])

    if new_size_ratio != 1.0:
        img = img.resize(
            (
                int(img.size[0] * new_size_ratio),
                int(img.size[1] * new_size_ratio),
            ),
            Image.Resampling.LANCZOS,
        )

    new_filename = join(
        folder,
        basename(file_path),
    )
    try:
        img.save(new_filename, optimize=True)
    except OSError:
        img = img.convert("RGB")
        img.save(new_filename, optimize=True)

    return new_filename


def _generate_page_thumbnails(
    issue_id: int,
    file_path: str,
) -> list[str]:
    """
    Generates a thumbnail of every page inside a book and returns
    a list of their corresponding file names
    """
    volume_id = FilesDB.volume_of_file(file_path)

    extension = file_path.split(".")[-1]

    if not volume_id or extension not in ("cbr", "cbz"):
        return []

    original_pages = extract_files(file_path)

    thumbnails_folder = _get_thumbnails_folder(issue_id, file_path)

    create_folder(thumbnails_folder)

    new_pages: list[str] = []

    for page in original_pages:
        new_pages.append(_generate_thumbnail(page, thumbnails_folder))

    volume_folder = Volume(volume_id).vd.folder
    delete_file_folder(generate_archive_folder(volume_folder, file_path))

    return new_pages


def _get_thumbnails_data(thumbnails: list[str]) -> list[ThumbnailData]:
    thumbnails_data: list[ThumbnailData] = []

    filenames = [basename(thumbnail) for thumbnail in thumbnails]
    prefix = get_files_prefix(filenames)

    for thumbnail, filename in zip(thumbnails, filenames):
        thumbnails_data.append(ThumbnailData(
            filepath=thumbnail,
            filename=filename,
            prefix=prefix,
        ))

    return thumbnails_data


def get_issue_page_thumbnails(
    issue_id: int,
    file_path: str,
    refresh=False,
) -> list[ThumbnailData]:
    if refresh:
        return _get_thumbnails_data(_generate_page_thumbnails(issue_id, file_path))

    thumbnails_folder = _get_thumbnails_folder(issue_id, file_path)

    if exists(thumbnails_folder):
        return _get_thumbnails_data(list_files(thumbnails_folder))
    else:
        return _get_thumbnails_data(_generate_page_thumbnails(issue_id, file_path))


def get_issue_page_thumbnail(page: str) -> BytesIO:
    with open(page, "rb") as fh:
        buf = BytesIO(fh.read())
    return buf


def update_issue_pages(file_id: int, new_pages: list[ThumbnailData]) -> None:
    if len(new_pages) == 0:
        return

    file = FilesDB.fetch(file_id=file_id)[0]["filepath"]

    is_rar = file.endswith(".cbr")

    if not file.endswith(".cbz") and not is_rar:
        return

    if is_rar:
        CBRtoCBZ.convert(file)
        file = file.replace(".cbr", ".cbz")

    archive_folder = generate_archive_folder(dirname(file), file)

    with ZipFile(file, "r") as zip:
        files = zip.namelist()
        zip.extractall(archive_folder)

    with ZipFile(file, "w") as zip:
        for f in files:
            for page in new_pages:
                if f == basename(page["filepath"]):
                    zip.write(filename=join(archive_folder, f), arcname=page["filename"])

    delete_file_folder(archive_folder)
    delete_file_folder(dirname(new_pages[0]["filepath"]))

    if is_rar:
        CBZtoCBR.convert(file)
    return
