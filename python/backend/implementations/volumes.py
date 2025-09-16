from __future__ import annotations

from asyncio import run
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from functools import lru_cache
from io import BytesIO
from os.path import dirname, exists, isdir, relpath
from re import IGNORECASE, compile
from time import time
from typing import TYPE_CHECKING, Any, assert_never

from backend.base.custom_exceptions import (
    InvalidKeyValue,
    IssueNotFound,
    TaskForVolumeRunning,
    VolumeAlreadyAdded,
    VolumeDownloadedFor,
    VolumeFolderInvalid,
    VolumeNotFound,
)
from backend.base.definitions import (
    SCANNABLE_EXTENSIONS,
    Constants,
    FileData,
    GeneralFileData,
    GeneralFileType,
    IssueData,
    IssueFileData,
    LibraryFilter,
    LibrarySorting,
    MonitorScheme,
    SpecialVersion,
    VolumeData,
)
from backend.base.file_extraction import extract_filename_data
from backend.base.files import (
    change_basefolder,
    create_folder,
    delete_empty_child_folders,
    delete_empty_parent_folders,
    delete_file_folder,
    folder_is_inside_folder,
    list_files,
    rename_file,
)
from backend.base.helpers import (
    PortablePool,
    extract_year_from_date,
    filtered_iter,
    first_of_subarrays,
    force_range,
    to_number_cv_id,
)
from backend.base.logging import LOGGER
from backend.implementations.comicvine import ComicVine
from backend.implementations.matching import _match_title, file_importing_filter
from backend.implementations.root_folders import RootFolders
from backend.internals.db import commit, get_db, rollback
from backend.internals.db_models import FilesDB, GeneralFilesDB
from backend.internals.server import WebSocket
from backend.internals.settings import Settings

if TYPE_CHECKING:
    from backend.base.definitions import Download

THIRTY_DAYS = timedelta(days=30)
SECONDS_IN_DAY = 86400
# autopep8: off
split_regex = compile(
    r"(?<!vs)(?<!r\.i\.p)(?:(?<=[\.!\?])\s|(?<=[\.!\?]</p>)(?!$))", IGNORECASE
)
remove_link_regex = compile(r"<a[^>]*>.*?</a>", IGNORECASE)
os_regex = compile(r"(?<!preceding\s)\bone[\- ]?shot\b(?!\scollections?)", IGNORECASE)
hc_regex = compile(r"(?<!preceding\s)\bhard[\- ]?cover\b(?!\scollections?)", IGNORECASE)
vol_regex = compile(r"^v(?:ol(?:ume)?)?\.?\s\d+(?:\:\s|$)", IGNORECASE)
# autopep8: on


# =====================
# region Issue
# =====================
class Issue:
    def __init__(self, id: int, check_existence: bool = False) -> None:
        """Create instance of issue.

        Args:
            id (int): The ID of the issue.
            check_existence (bool, optional): Check if issue exists based on ID.
                Defaults to False.

        Raises:
            IssueNotFound: The issue was not found.
                Can only be raised when check_existence is `True`.
        """
        self.id = id

        if not check_existence:
            return

        issue_id = (
            get_db()
            .execute("SELECT id FROM issues WHERE id = ? LIMIT 1;", (self.id,))
            .fetchone()
        )

        if issue_id is None:
            raise IssueNotFound(id)
        return

    @classmethod
    @lru_cache(maxsize=3)
    def from_volume_and_calc_number(
        cls, volume_id: int, calculated_issue_number: float
    ) -> Issue:
        """Create instance of issue based on volume ID and calculated issue
        number of issue.

        Args:
            volume_id (int): The ID of the volume that the issue is in.
            calculated_issue_number (float): The calculated issue number of
            the issue.

        Raises:
            IssueNotFound: No issue found with the given arguments.

        Returns:
            Issue: The issue instance.
        """
        issue_id: int | None = (
            get_db()
            .execute(
                """
            SELECT id
            FROM issues
            WHERE volume_id = ?
                AND calculated_issue_number = ?
            LIMIT 1;
            """,
                (volume_id, calculated_issue_number),
            )
            .exists()
        )

        if not issue_id:
            raise IssueNotFound(-1)

        return cls(issue_id, check_existence=True)

    def get_data(self) -> IssueData:
        """Get data about the issue.

        Returns:
            dict: The data.
        """
        data = (
            get_db()
            .execute(
                """
            SELECT
                id, volume_id, comicvine_id,
                issue_number, calculated_issue_number,
                title, date, description,
                monitored
            FROM issues
            WHERE id = ?
            LIMIT 1;
            """,
                (self.id,),
            )
            .fetchonedict()
            or {}
        )

        return IssueData(**data, files=self.get_files())  # type: ignore

    def get_files(self) -> list[FileData]:
        """Get all files linked to the issue.

        Returns:
            List[FileData]: List of file datas.
        """
        return FilesDB.fetch(issue_id=self.id)

    def __format_value(self, key: str, value: Any) -> Any:
        converted_value = value

        if key == "monitored" and not isinstance(converted_value, bool):
            raise InvalidKeyValue(key, value)

        return converted_value

    def update(self, data: Mapping[str, Any]) -> None:
        """Change aspects of the issue, in a `dict.update()` type of way.

        Args:
            data (Mapping[str, Any]): The keys and their new values.

        Raises:
            KeyError: Key is not allowed.
            InvalidKeyValue: Value of key is not allowed.
        """
        allowed_keys: Sequence[str] = (
            "monitored",
            "title",
            "date",
            "description",
        )

        formatted_data = {}

        for key, value in data.items():
            if key not in allowed_keys:
                raise KeyError
            if key in allowed_keys:
                if key == "monitored":
                    formatted_data[key] = self.__format_value(key, value)
                else:
                    formatted_data[key] = value

        cursor = get_db()
        for key, value in formatted_data.items():
            cursor.execute(
                f"UPDATE issues SET {key} = ? WHERE id = ?;", (value, self.id)
            )

        LOGGER.info(f"For issue {self.id}, changed: {formatted_data}")
        return

    def __setitem__(self, __name: str, __value: Any) -> None:
        """Change an aspect of the issue.

        Args:
            __name (str): The key of the aspect.
            __value (Any): The new value of the aspect.

        Raises:
            KeyError: Key is not allowed.
            InvalidKeyValue: Value of key is not allowed.
        """
        self.update({__name: __value})
        return

    def delete(self) -> None:
        """Delete the issue from the database."""
        FilesDB.delete_issue_linked_files(self.id)
        get_db().execute("DELETE FROM issues WHERE id = ?;", (self.id,))
        return


# =====================
# region Volume
# =====================
class Volume:
    def __init__(self, id: int, check_existence: bool = False) -> None:
        """Create instance of Volume.

        Args:
            id (int): The ID of the volume.
            check_existence (bool, optional): Check if volume exists, based on ID.
                Defaults to False.

        Raises:
            VolumeNotFound: The volume was not found.
                Can only be raised when check_existence is `True`.
        """
        self.id = id

        if not check_existence:
            return

        volume_id = (
            get_db()
            .execute("SELECT id FROM volumes WHERE id = ? LIMIT 1;", (self.id,))
            .fetchone()
        )

        if volume_id is None:
            raise VolumeNotFound(id)
        return

    def get_data(self) -> VolumeData:
        data = (
            get_db()
            .execute(
                """
            SELECT
                id, comicvine_id, libgen_url,
                title, alt_title,
                year, publisher, volume_number,
                description, site_url,
                monitored, monitor_new_issues,
                root_folder, folder, custom_folder,
                special_version, special_version_locked,
                last_cv_fetch
            FROM volumes
            WHERE id = ?
            LIMIT 1;
            """,
                (self.id,),
            )
            .fetchonedict()
            or {}
        )

        return VolumeData(
            **{**data, "special_version": SpecialVersion(data["special_version"])}
        )

    def get_public_keys(self) -> dict:
        """Get data about the volume for the public to see (the API).

        Returns:
            dict: The data.
        """
        volume_info = (
            get_db()
            .execute(
                """
            SELECT
                v.id, comicvine_id, libgen_url,
                title, year, publisher,
                volume_number,
                special_version, special_version_locked,
                description, site_url,
                monitored, monitor_new_issues,
                v.folder, root_folder,
                rf.folder AS root_folder_path,
                (
                    SELECT COUNT(*)
                    FROM issues
                    WHERE volume_id = v.id
                ) AS issue_count,
                (
                    SELECT COUNT(DISTINCT issue_id)
                    FROM issues i
                    INNER JOIN issues_files if
                    ON i.id = if.issue_id
                    WHERE volume_id = v.id
                ) AS issues_downloaded,
                (
                    SELECT SUM(size) FROM (
                        SELECT DISTINCT f.id, size
                        FROM issues i
                        INNER JOIN issues_files if
                        INNER JOIN files f
                        ON i.id = if.issue_id
                            AND if.file_id = f.id
                        WHERE volume_id = v.id
                    )
                ) AS total_size
            FROM volumes v
            INNER JOIN root_folders rf
            ON v.root_folder = rf.id
            WHERE v.id = ?
            LIMIT 1;
            """,
                (self.id,),
            )
            .fetchonedict()
            or {}
        )
        volume_info["volume_folder"] = relpath(
            volume_info["folder"], volume_info["root_folder_path"]
        )
        del volume_info["root_folder_path"]
        volume_info["issues"] = [i.as_dict() for i in self.get_issues()]
        volume_info["general_files"] = self.get_general_files()

        return volume_info

    @property
    def vd(self) -> VolumeData:
        return self.get_data()

    def get_cover(self) -> BytesIO:
        """Get the cover of the volume.

        Returns:
            BytesIO: The cover.
        """
        cover = (
            get_db()
            .execute("SELECT cover FROM volumes WHERE id = ? LIMIT 1", (self.id,))
            .fetchone()[0]
        )
        return BytesIO(cover)

    def get_ending_year(self) -> int | None:
        """Get the year of the last issue that has a release date.

        Returns:
            int | None: The release year of the last issue with a release
            date set. `None` if there is no issue or no issue with a release
            date.
        """
        last_issue_date = (
            get_db()
            .execute(
                """
            SELECT MAX(date) AS last_issue_date
            FROM issues
            WHERE volume_id = ?;
            """,
                (self.id,),
            )
            .exists()
        )

        return extract_year_from_date(last_issue_date)

    def get_issue(self, issue_id: int) -> Issue:
        return Issue(issue_id)

    def get_issues(self, _skip_files: bool = False) -> list[IssueData]:
        """Get list of issues that are in the volume.

        Args:
            _skip_files (bool, optional): Don't fetch the files matched to
            each issue. Saves quite a bit of time.
                Defaults to False.

        Returns:
            List[IssueData]: The list of issues.
        """
        cursor = get_db()
        issues = cursor.execute(
            """
            SELECT
                id, volume_id, comicvine_id,
                issue_number, calculated_issue_number,
                title, date, description,
                monitored
            FROM issues
            WHERE volume_id = ?
            ORDER BY date, calculated_issue_number
            """,
            (self.id,),
        ).fetchalldict()

        file_mapping: dict[int, list[FileData]] = {}
        if not _skip_files:
            cursor.execute(
                """
                SELECT i.id AS issue_id, f.id AS file_id, filepath, size, releaser, scan_type, resolution, dpi
                FROM files f
                INNER JOIN issues_files if
                    ON f.id = if.file_id
                INNER JOIN issues i
                    ON if.issue_id = i.id
                WHERE i.volume_id = ?
                ORDER BY filepath;
                """,
                (self.id,),
            )
            for file in cursor:
                file_mapping.setdefault(file[0], []).append(
                    {
                        "id": file["file_id"],
                        "filepath": file["filepath"],
                        "size": file["size"],
                        "releaser": file["releaser"],
                        "scan_type": file["scan_type"],
                        "resolution": file["resolution"],
                        "dpi": file["dpi"],
                    }
                )

        result = []

        for i in issues:
            final_files = file_mapping.get(i["id"]) or []

            final_files_data = [
                IssueFileData(
                    {
                        **file,
                        **extract_filename_data(file["filepath"]),
                    }
                )
                for file in final_files
            ]
            result.append(IssueData(**i, files=final_files_data))

        return result

    def get_issues_in_range(
        self,
        calculated_issue_number_start: float | int,
        calculated_issue_number_end: float | int,
    ) -> list[IssueData]:
        """Return a list of issues that are between two calculated issue numbers.
        Files of the issues are not fetched.

        Args:
            calculated_issue_number_start (Union[float, int]): The start of the
            range.
            calculated_issue_number_end (Union[float, int]): The end of the
            range.

        Returns:
            List[IssueData]: The list of issues in the range.
        """
        return [
            issue
            for issue in sorted(
                self.get_issues(_skip_files=True),
                key=lambda i: i.calculated_issue_number,
            )
            if (
                calculated_issue_number_start
                <= issue.calculated_issue_number
                <= calculated_issue_number_end
            )
        ]

    def get_open_issues(self) -> list[tuple[int, float]]:
        """Get the issues that are not matched to a file and are monitored.

        Returns:
            List[Tuple[int, float]]: The id and calculated issue numbers of
            the open issues.
        """
        return (
            get_db()
            .execute(
                """
            SELECT i.id, i.calculated_issue_number
            FROM issues i
            LEFT JOIN issues_files if
            ON i.id = if.issue_id
            WHERE
                file_id IS NULL
                AND volume_id = ?
                AND monitored = 1;
            """,
                (self.id,),
            )
            .fetchall()
        )

    def get_all_files(self) -> list[FileData]:
        """Get the files and general files matched to the volume.

        Returns:
            List[FileData]: List of files.
        """
        result = FilesDB.fetch(volume_id=self.id)
        result.extend(GeneralFilesDB.fetch(self.id))
        return result

    def get_general_files(self) -> list[GeneralFileData]:
        """Get the general files linked to the volume.

        Returns:
            List[GeneralFileData]: The general files.
        """
        return GeneralFilesDB.fetch(self.id)

    def update(self, data: Mapping[str, Any], from_public: bool = False) -> None:
        allowed_keys: Sequence[str]

        if from_public:
            allowed_keys = (
                "monitored",
                "monitor_new_issues",
                "special_version",
                "special_version_locked",
                "libgen_url",
            )
        else:
            allowed_keys = (*VolumeData.__annotations__, "cover")

        for key in data:
            if key not in allowed_keys:
                raise KeyError

        cursor = get_db()
        for key, value in data.items():
            cursor.execute(
                f"UPDATE volumes SET {key} = ? WHERE id = ?;", (value, self.id)
            )

        return

    def __setitem__(self, __name: str, __value: Any) -> None:
        """Change an aspect of the issue.

        Args:
            __name (str): The key of the aspect.
            __value (Any): The new value of the aspect.

        Raises:
            KeyError: Key is not allowed.
            InvalidKeyValue: Value of key is not allowed.
        """
        self.update({__name: __value})
        return

    def apply_monitor_scheme(self, monitoring_scheme: MonitorScheme) -> None:
        """Apply a monitoring scheme to the issues of the volume.

        Args:
            monitoring_scheme (MonitorScheme): The monitoring scheme to apply.
        """
        cursor = get_db()

        if monitoring_scheme == MonitorScheme.NONE:
            cursor.execute(
                """
                UPDATE issues
                SET monitored = 0
                WHERE volume_id = ?;
                """,
                (self.id,),
            )

        elif monitoring_scheme == MonitorScheme.MISSING:
            cursor.execute(
                """
                WITH missing_issues AS (
                    SELECT id
                    FROM issues i
                    LEFT JOIN issues_files if
                    ON i.id = if.issue_id
                    WHERE volume_id = ?
                        AND if.issue_id IS NULL
                )
                UPDATE issues
                SET monitored = 0
                WHERE
                    volume_id = ?
                    AND id NOT IN missing_issues;
                """,
                (self.id, self.id),
            )

        elif monitoring_scheme == MonitorScheme.ALL:
            cursor.execute(
                """
                UPDATE issues
                SET monitored = 1
                WHERE volume_id = ?;
                """,
                (self.id,),
            )

        else:
            assert_never(monitoring_scheme)  # type: ignore

        return

    def change_root_folder(self, new_root_folder_id: int) -> None:
        """Change the root folder of the volume.

        Args:
            new_root_folder_id (int): The root folder ID of the new root folder.
        """
        vd = self.get_data()
        if vd.root_folder == new_root_folder_id:
            return

        root_folders = RootFolders()
        current_root_folder = root_folders.get_one(vd.root_folder)
        new_root_folder = root_folders.get_one(new_root_folder_id)

        LOGGER.info(
            f"Changing root folder of volume {self.id} "
            f"from {current_root_folder.folder} to {new_root_folder.folder}"
        )

        file_changes = change_basefolder(
            (f["filepath"] for f in self.get_all_files()),
            current_root_folder.folder,
            new_root_folder.folder,
        )
        for old_name, new_name in file_changes.items():
            rename_file(old_name, new_name)
        if isdir(vd.folder):
            delete_empty_child_folders(vd.folder)

        FilesDB.update_filepaths(file_changes.keys(), file_changes.values())

        self["root_folder"] = new_root_folder.id
        self["folder"] = new_folder = change_basefolder(
            (vd.folder,), current_root_folder.folder, new_root_folder.folder
        )[vd.folder]

        delete_empty_parent_folders(vd.folder, current_root_folder.folder)

        if Settings().sv.create_empty_volume_folders:
            create_folder(new_folder)

        return

    def change_volume_folder(self, new_volume_folder: str | None) -> None:
        """Change the volume folder of the volume.

        Args:
            new_volume_folder (str | None): The new folder,
            or `None` if the default folder should be generated and used.
        """
        from backend.implementations.naming import generate_volume_folder_path

        vd = self.get_data()
        current_volume_folder = vd.folder
        root_folder = RootFolders()[vd.root_folder]
        new_volume_folder = generate_volume_folder_path(
            root_folder, new_volume_folder or self.id
        )

        if current_volume_folder == new_volume_folder:
            return

        LOGGER.info(
            f"Moving volume folder from {current_volume_folder} to {new_volume_folder}"
        )

        self["custom_folder"] = new_volume_folder is not None
        self["folder"] = new_volume_folder

        file_changes = change_basefolder(
            (f["filepath"] for f in self.get_all_files()),
            current_volume_folder,
            new_volume_folder,
        )
        for old_name, new_name in file_changes.items():
            rename_file(old_name, new_name)
        delete_empty_child_folders(current_volume_folder)

        FilesDB.update_filepaths(file_changes.keys(), file_changes.values())

        create_empty_volume_folders = Settings().sv.create_empty_volume_folders
        if create_empty_volume_folders:
            create_folder(new_volume_folder)

        if (create_empty_volume_folders or file_changes) and folder_is_inside_folder(
            new_volume_folder, current_volume_folder
        ):
            # New folder is parent of current folder, so delete up to new
            # folder.
            delete_empty_parent_folders(current_volume_folder, new_volume_folder)

        else:
            delete_empty_parent_folders(current_volume_folder, root_folder)

        return

    def delete(self, delete_folder: bool = False) -> None:
        """Delete the volume from the library.

        Args:
            delete_folder (bool, optional): Also delete the volume folder and
            it's contents.
                Defaults to False.

        Raises:
            TaskForVolumeRunning: There is a task in the queue for the volume.
            VolumeDownloadedFor: There is a download in the queue for the volume.
        """
        from backend.features.download_queue import DownloadHandler
        from backend.features.tasks import TaskHandler

        LOGGER.info(
            f"Deleting volume {self.id} with delete_folder set to {delete_folder}"
        )

        # Check if there is no task running for the volume
        if TaskHandler.task_for_volume_running(self.id):
            raise TaskForVolumeRunning(self.id)

        # Check if nothing is downloading for the volume
        if any(entry.volume_id == self.id for entry in DownloadHandler.queue):
            raise VolumeDownloadedFor(self.id)

        if delete_folder:
            vd = self.get_data()

            if exists(vd.folder):
                for f in self.get_all_files():
                    delete_file_folder(f["filepath"])

                delete_empty_child_folders(vd.folder)
                delete_empty_parent_folders(vd.folder, RootFolders()[vd.root_folder])

        # Delete file entries
        # ON DELETE CASCADE will take care of issues_files
        FilesDB.delete_linked_files(self.id)

        # Delete metadata entries
        # ON DELETE CASCADE will take care of issues
        get_db().execute("DELETE FROM volumes WHERE id = ?", (self.id,))

        return

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}; ID {self.id}>"


# =====================
# region Library
# =====================
class Library:
    def get_public_volumes(
        self,
        sort: LibrarySorting = LibrarySorting.TITLE,
        filter: LibraryFilter | int | None = None,
    ) -> list[dict]:
        """Get all volumes in the library

        Args:
            sort (LibrarySorting, optional): How to sort the list.
                Defaults to LibrarySorting.TITLE.

            filter (LibraryFilter | None, optional): Apply a filter to
            the list if not `None`.
                Defaults to None.

        Returns:
            List[dict]: The list of volumes in the library.
        """
        if isinstance(filter, LibraryFilter):
            sql_filter = filter.value
        elif isinstance(filter, int):
            sql_filter = f"WHERE comicvine_id = {filter}"
        else:
            sql_filter = ""

        volumes = (
            get_db()
            .execute(f"""
            WITH
                vol_issues AS (
                    SELECT id, monitored, date
                    FROM issues
                    WHERE volume_id = volumes.id
                ),
                issues_to_files AS (
                    SELECT issue_id, monitored, f.id, size
                    FROM issues i
                    INNER JOIN issues_files if
                    INNER JOIN files f
                    ON i.id = if.issue_id
                        AND if.file_id = f.id
                    WHERE volume_id = volumes.id
                )
            SELECT
                id, comicvine_id,
                title, year, publisher,
                volume_number, description,
                monitored, monitor_new_issues,
                folder,
                (
                    SELECT COUNT(size) FROM (SELECT size FROM issues_to_files)
                ) AS issue_file_count,
                (
                    SELECT COUNT(id) FROM vol_issues
                ) AS issue_count,
                (
                    SELECT COUNT(id) FROM vol_issues WHERE monitored = 1
                ) AS issue_count_monitored,
                (
                    SELECT COUNT(DISTINCT issue_id) FROM issues_to_files
                ) AS issues_downloaded,
                (
                    SELECT COUNT(DISTINCT issue_id) FROM issues_to_files WHERE monitored = 1
                ) AS issues_downloaded_monitored,
                (
                    SELECT SUM(size) FROM (SELECT DISTINCT id, size FROM issues_to_files)
                ) AS total_size
            FROM volumes
            {sql_filter}
            ORDER BY {sort.value};
            """)
            .fetchalldict()
        )

        return volumes

    def search(
        self,
        query: str,
        sort: LibrarySorting = LibrarySorting.TITLE,
        filter: LibraryFilter | None = None,
    ) -> list[dict]:
        """Search in the library with a query.

        Args:
            query (str): The query to search with.

            sort (LibrarySorting, optional): How to sort the list.
                Defaults to LibrarySorting.TITLE.

            filter (LibraryFilter | None, optional): Apply a filter to
            the list if not `None`.
                Defaults to None.

        Returns:
            List[dict]: The resulting list of matching volumes in the library.
        """
        if query.startswith(("4050-", "cv:")):
            try:
                cv_id = to_number_cv_id((query,))[0]
                volumes = self.get_public_volumes(sort, cv_id)

            except ValueError:
                volumes = []

        else:
            volumes = [
                v
                for v in self.get_public_volumes(sort, filter)
                if _match_title(v["title"], query, allow_contains=True)
            ]

        return volumes

    def get_stats(self) -> dict[str, int]:
        result = (
            get_db()
            .execute("""
            WITH v AS (
                SELECT COUNT(*) AS volumes,
                    SUM(monitored) AS monitored
                FROM volumes
            )
            SELECT
                v.volumes,
                v.monitored,
                v.volumes - v.monitored AS unmonitored,
                (SELECT COUNT(*) FROM issues) AS issues,
                (SELECT COUNT(DISTINCT issue_id) FROM issues_files) AS downloaded_issues,
                (SELECT COUNT(*) FROM files) AS files,
                (SELECT IFNULL(SUM(size), 0) FROM files) AS total_file_size
            FROM v;
        """)
            .fetchonedict()
            or {}
        )
        return result

    def get_volumes(self) -> list[int]:
        """Get a list of the ID's of all the volumes.

        Returns:
            List[int]: The list of ID's.
        """
        return first_of_subarrays(get_db().execute("SELECT id FROM volumes;"))

    def get_volume(self, volume_id: int) -> Volume:
        """Get a volume from the library.

        Args:
            volume_id (int): The ID of the volume.

        Raises:
            VolumeNotFound: The ID doesn't map to any volume in the library.

        Returns:
            Volume: The volume.
        """
        return Volume(volume_id, check_existence=True)

    def get_issue(self, issue_id: int) -> Issue:
        """Get an issue from the library.

        Args:
            issue_id (int): The ID of the issue.

        Raises:
            IssueNotFound: The ID doesn't map to any issue in the library.

        Returns:
            Issue: The issue.
        """
        return Issue(issue_id, check_existence=True)

    def _volume_added(self, comicvine_id: int) -> bool:
        """Check if a volume is in the library.

        Args:
            comicvine_id (int): The CV ID of the volume to check for.

        Returns:
            bool: Whether a volume with the given CV ID is in the library.
        """
        return (
            get_db()
            .execute(
                "SELECT 1 FROM volumes WHERE comicvine_id = ? LIMIT 1;", (comicvine_id,)
            )
            .exists()
            is not None
        )

    def add(
        self,
        comicvine_id: int,
        root_folder_id: int,
        monitored: bool,
        monitor_scheme: MonitorScheme = MonitorScheme.ALL,
        monitor_new_issues: bool = True,
        volume_folder: str | None = None,
        special_version: SpecialVersion | None = None,
        auto_search: bool = False,
    ) -> int:
        """Add a volume to the library.

        Args:
            comicvine_id (int): The CV ID of the volume.

            root_folder_id (int): The ID of the rootfolder in which
            the volume folder will be.

            monitored (bool): Whether the volume should be monitored.

            monitor_scheme (MonitorScheme, optional): Which issues to monitor.
                Defaults to `MonitorScheme.ALL`.

            monitor_new_issues (bool, optional): Whether to monitor new issues.
                Defaults to True.

            volume_folder (str | None, optional): Custom volume folder.
                Defaults to None.

            special_version (SpecialVersion | None, optional): Give `None`
            to let Kapowarr determine the special version ('auto'). Otherwise,
            give a `SpecialVersion` to override and lock the special version
            state.
                Defaults to None.

            auto_search (bool, optional): Start an auto search for the volume after
            adding it.
                Defaults to False.

        Raises:
            RootFolderNotFound: The root folder with the given ID was not found.
            VolumeFolderInvalid: The volume folder is the parent or child of
            another volume folder.
            VolumeAlreadyAdded: The volume already exists in the library.
            CVRateLimitReached: The ComicVine API rate limit is reached.

        Returns:
            int: The new ID of the volume.
        """
        from backend.implementations.naming import generate_volume_folder_path

        LOGGER.info(
            "Adding a volume to the library: "
            "CV ID %d, RF ID %d, M %s, MS %s, MNI %s, VF %s, SV %s",
            comicvine_id,
            root_folder_id,
            monitored,
            monitor_scheme.value,
            monitor_new_issues,
            volume_folder,
            special_version,
        )

        if self._volume_added(comicvine_id):
            raise VolumeAlreadyAdded(comicvine_id)

        # Raises RootFolderNotFound when ID is invalid
        root_folder = RootFolders().get_one(root_folder_id)

        vd = run(ComicVine().fetch_volume(comicvine_id))

        cursor = get_db()
        with cursor:
            volume_id = cursor.execute(
                """
                INSERT INTO volumes(
                    comicvine_id,
                    title,
                    alt_title,
                    year,
                    publisher,
                    volume_number,
                    description,
                    site_url,
                    cover,
                    monitored,
                    monitor_new_issues,
                    root_folder,
                    custom_folder,
                    last_cv_fetch,
                    special_version,
                    special_version_locked
                ) VALUES (
                    :comicvine_id, :title, :alt_title,
                    :year, :publisher, :volume_number, :description,
                    :site_url, :cover, :monitored, :monitor_new_issues,
                    :root_folder, :custom_folder,
                    :last_cv_fetch, :special_version, :special_version_locked
                );
                """,
                {
                    "comicvine_id": vd["comicvine_id"],
                    "title": vd["title"],
                    "alt_title": (vd["aliases"] or [None])[0],
                    "year": vd["year"],
                    "publisher": vd["publisher"],
                    "volume_number": vd["volume_number"],
                    "description": vd["description"],
                    "site_url": vd["site_url"],
                    "cover": vd["cover"],
                    "monitored": monitored,
                    "monitor_new_issues": monitor_new_issues,
                    "root_folder": root_folder.id,
                    "custom_folder": volume_folder is not None,
                    "last_cv_fetch": round(time()),
                    "special_version": None,
                    "special_version_locked": special_version is not None,
                },
            ).lastrowid

            cursor.executemany(
                """
                INSERT INTO issues(
                    volume_id,
                    comicvine_id,
                    issue_number,
                    calculated_issue_number,
                    title,
                    date,
                    description,
                    monitored
                ) VALUES (
                    :volume_id, :comicvine_id,
                    :issue_number, :calculated_issue_number,
                    :title, :date, :description,
                    :monitored
                );
                """,
                (
                    {
                        "volume_id": volume_id,
                        "comicvine_id": i["comicvine_id"],
                        "issue_number": i["issue_number"],
                        "calculated_issue_number": i["calculated_issue_number"],
                        "title": i["title"],
                        "date": i["date"],
                        "description": i["description"],
                        "monitored": True,
                    }
                    for i in vd["issues"] or []
                ),
            )

            volume = Volume(volume_id)

            if special_version is None:
                special_version = determine_special_version(volume.id)
            volume["special_version"] = special_version

            folder = generate_volume_folder_path(
                root_folder.folder, volume_folder or volume_id
            )

            # Check whether volume folder is parent or child of other volume
            # folder
            for other_vf in cursor.execute(
                "SELECT folder FROM volumes WHERE id != ?;", (volume_id,)
            ):
                if folder != other_vf[0] and (
                    folder_is_inside_folder(folder, other_vf[0])
                    or folder_is_inside_folder(other_vf[0], folder)
                ):
                    rollback()
                    raise VolumeFolderInvalid(folder)

            volume["folder"] = folder

            if Settings().sv.create_empty_volume_folders:
                create_folder(folder)
                scan_files(volume_id)

            volume.apply_monitor_scheme(monitor_scheme)

        if auto_search:
            from backend.features.tasks import AutoSearchVolume, TaskHandler

            # Volume is accessed from different thread so changes must be saved,
            # but that's already done by the completion of the transaction above
            task = AutoSearchVolume(volume_id)
            TaskHandler().add(task)

        LOGGER.info(f"Added volume with CV ID {comicvine_id} and ID {volume_id}")
        return volume_id


# =====================
# region Scanning and updating
# =====================
def determine_special_version(volume_id: int) -> SpecialVersion:
    """Determine if a volume is a special version.

    Args:
        volume_id (int): The ID of the volume to determine for.

    Returns:
        SpecialVersion: The result.
    """
    volume = Volume(volume_id)
    volume_data = volume.get_data()
    issues = volume.get_issues()
    one_issue = len(issues) == 1

    if issues and all(vol_regex.search(i.title or "") for i in issues):
        return SpecialVersion.VOLUME_AS_ISSUE

    if one_issue:
        if os_regex.search(volume_data.title):
            return SpecialVersion.ONE_SHOT

        if hc_regex.search(volume_data.title):
            return SpecialVersion.HARD_COVER

        if (issues[0].title or "").lower().replace(" ", "") in (
            "hc",
            "hard-cover",
            "hardcover",
        ):
            return SpecialVersion.HARD_COVER

        if (issues[0].title or "").lower().replace(" ", "") in (
            "os",
            "one-shot",
            "oneshot",
        ):
            return SpecialVersion.ONE_SHOT

    if "annual" in volume_data.title.lower():
        # Volume is annual
        return SpecialVersion.NORMAL

    if one_issue and volume_data.description:
        # Look for Special Version in first sentence of description.
        # Only first sentence as to avoid false hits (e.g. referring in desc
        # to other volume that is Special Version à la
        # "Also available as one shot")
        first_sentence = split_regex.split(volume_data.description)[0]
        first_sentence = remove_link_regex.sub("", first_sentence)
        if os_regex.search(first_sentence):
            return SpecialVersion.ONE_SHOT

        if hc_regex.search(first_sentence):
            return SpecialVersion.HARD_COVER

    if one_issue and issues[0].date:
        thirty_plus_days_ago = (
            datetime.now() - datetime.strptime(issues[0].date, "%Y-%m-%d") > THIRTY_DAYS
        )

        if thirty_plus_days_ago:
            return SpecialVersion.TPB

    return SpecialVersion.NORMAL


def scan_files(
    volume_id: int,
    filepath_filter: list[str] = [],
    del_unmatched_files: bool = True,
    update_websocket: bool = False,
    download: Download | None = None,
) -> None:
    """Scan inside the volume folder for files and map them to issues.

    Args:
        volume_id (int): The ID of the volume to scan for.

        filepath_filter (List[str], optional): Only scan specific files.
        Intended for adding files to a volume only.
            Defaults to [].

        del_unmatched_files (bool, optional): Delete file entries in the DB
        that aren't linked to anything anymore.
            Defaults to True.

        update_websocket (bool, optional): Send websocket messages on changes
        about the download status of the issues.
            Defaults to False.
    """
    LOGGER.debug(f"Scanning for files for {volume_id}")

    settings = Settings().get_settings()
    volume = Volume(volume_id)
    volume_data = volume.get_data()

    if not isdir(volume_data.folder):
        if settings.create_empty_volume_folders:
            create_folder(volume_data.folder)
        else:
            return

    volume_issues = volume.get_issues(_skip_files=True)
    general_files = tuple(
        (gf["id"], gf["file_type"]) for gf in volume.get_general_files()
    )
    volume_files = {f["filepath"]: f["id"] for f in volume.get_all_files()}
    number_to_year: dict[float, int | None] = {
        i.calculated_issue_number: extract_year_from_date(i.date) for i in volume_issues
    }

    bindings: list[tuple[int, int]] = []
    general_bindings: list[tuple[int, str]] = []
    folder_contents = list_files(folder=volume_data.folder, ext=SCANNABLE_EXTENSIONS)
    for file in filtered_iter(folder_contents, set(filepath_filter)):
        file_data = extract_filename_data(file)

        # Check if file matches volume
        if not file_importing_filter(
            file_data, volume_data, volume_issues, number_to_year
        ):
            continue

        if (
            file_data["special_version"] == SpecialVersion.COVER
            and file_data["issue_number"] is None
        ):
            # Volume cover file
            if file not in volume_files:
                volume_files[file] = FilesDB.add_file(file, download)

            general_bindings.append((volume_files[file], GeneralFileType.COVER.value))

        elif (
            file_data["special_version"] == SpecialVersion.METADATA
            and file_data["issue_number"] is None
        ):
            # Volume metadata file
            if file not in volume_files:
                volume_files[file] = FilesDB.add_file(file, download)

            general_bindings.append(
                (volume_files[file], GeneralFileType.METADATA.value)
            )

        elif (
            volume_data.special_version
            not in (SpecialVersion.VOLUME_AS_ISSUE, SpecialVersion.NORMAL)
            and file_data["special_version"]
        ):
            # Special Version
            if file not in volume_files:
                volume_files[file] = FilesDB.add_file(file, download)

            bindings.append((volume_files[file], volume_issues[0].id))

        elif (
            file_data["issue_number"] is not None
            or volume_data.special_version == SpecialVersion.VOLUME_AS_ISSUE
        ):
            # Normal issue
            issue_range = file_data["issue_number"]
            if (
                volume_data.special_version == SpecialVersion.VOLUME_AS_ISSUE
                and file_data["issue_number"] is None
            ):
                issue_range = file_data["volume_number"]

            matching_issues = volume.get_issues_in_range(
                *force_range(issue_range)  # type: ignore
            )

            if matching_issues:
                if file not in volume_files:
                    volume_files[file] = FilesDB.add_file(file, download)

                for issue in matching_issues:
                    bindings.append((volume_files[file], issue.id))

    cursor = get_db()

    # Find out what exactly is deleted, added, which issues are now downloaded,
    # and which are now not downloaded
    current_bindings: list[tuple[int, int]] = [
        tuple(b)
        for b in cursor.execute(
            """
            SELECT if.file_id, if.issue_id
            FROM issues_files if
            INNER JOIN issues i
            ON if.issue_id = i.id
            WHERE i.volume_id = ?;
            """,
            (volume_id,),
        )
    ]
    delete_bindings = tuple(b for b in current_bindings if b not in bindings)
    add_bindings = tuple(b for b in bindings if b not in current_bindings)
    issue_binding_count = {}
    for file_id, issue_id in current_bindings:
        issue_binding_count[issue_id] = issue_binding_count.setdefault(issue_id, 0) + 1

    newly_downloaded_issues: list[int] = []
    for file_id, issue_id in add_bindings:
        if issue_binding_count.setdefault(issue_id, 0) == 0:
            newly_downloaded_issues.append(issue_id)
        issue_binding_count[issue_id] += 1

    # This list is only valid if there isn't a filepath_filter
    deleted_downloaded_issues: list[int] = []
    for file_id, issue_id in delete_bindings:
        issue_binding_count[issue_id] -= 1
        if issue_binding_count[issue_id] == 0:
            deleted_downloaded_issues.append(issue_id)

    del current_bindings
    del issue_binding_count

    if not filepath_filter:
        # Delete bindings that aren't in new bindings
        cursor.executemany(
            "DELETE FROM issues_files WHERE file_id = ? AND issue_id = ?;",
            delete_bindings,
        )

        if settings.unmonitor_deleted_issues:
            cursor.executemany(
                "UPDATE issues SET monitored = 0 WHERE id = ?;",
                ((issue_id,) for issue_id in deleted_downloaded_issues),
            )

    # Add bindings that aren't in current bindings
    cursor.executemany(
        "INSERT INTO issues_files(file_id, issue_id) VALUES (?, ?);", add_bindings
    )
    if update_websocket:
        if not filepath_filter and (
            deleted_downloaded_issues or newly_downloaded_issues
        ):
            WebSocket().update_downloaded_status(
                volume_id,
                not_downloaded_issues=deleted_downloaded_issues,
                downloaded_issues=newly_downloaded_issues,
            )

        elif filepath_filter and newly_downloaded_issues:
            WebSocket().update_downloaded_status(
                volume_id, downloaded_issues=newly_downloaded_issues
            )

    # Delete bindings for general files that aren't in new bindings
    if not filepath_filter:
        delete_general_bindings = (
            (b[0],) for b in general_files if b not in general_bindings
        )
        cursor.executemany(
            "DELETE FROM volume_files WHERE file_id = ?;", delete_general_bindings
        )

    # Add bindings for general files that aren't in current bindings
    cursor.executemany(
        """
        INSERT OR IGNORE INTO volume_files(
            file_id, file_type, volume_id
        ) VALUES (?, ?, ?);
        """,
        ((b[0], b[1], volume_id) for b in general_bindings),
    )

    if del_unmatched_files:
        FilesDB.delete_unmatched_files()

    commit()

    if settings.delete_empty_folders:
        delete_empty_child_folders(volume_data.folder)
        if (
            not list_files(volume_data.folder)
            and not settings.create_empty_volume_folders
        ):
            delete_empty_parent_folders(
                volume_data.folder, RootFolders()[volume_data.root_folder]
            )

    return


def refresh_and_scan(
    volume_id: int | None = None,
    update_websocket: bool = False,
    allow_skipping: bool = True,
) -> None:
    """Refresh and scan one or more volumes.

    Args:
        volume_id (int | None, optional): The id of the volume if it is
        desired to only refresh and scan one. If left to `None`, all volumes are
        refreshed and scanned.
            Defaults to None.

        update_websocket (bool, optional): Send task progress updates over
        the websocket.
            Defaults to False.

        allow_skipping (bool, optional): Skip volumes that have been updated in
        the last 24 hours or that still have the same amount of issues.
            Defaults to True.
    """
    cursor = get_db()

    one_day_ago = round(time()) - SECONDS_IN_DAY
    five_days_ago = round(time()) - (5 * SECONDS_IN_DAY)
    if volume_id:
        cursor.execute(
            """
            SELECT comicvine_id, id, last_cv_fetch
            FROM volumes
            WHERE id = ?
            LIMIT 1;
            """,
            (volume_id,),
        )

    elif not allow_skipping:
        cursor.execute("""
            SELECT comicvine_id, id, last_cv_fetch
            FROM volumes
            ORDER BY last_cv_fetch ASC;
            """)

    else:
        cursor.execute(
            """
            SELECT comicvine_id, id, last_cv_fetch
            FROM volumes
            WHERE last_cv_fetch <= ?
            ORDER BY last_cv_fetch ASC;
            """,
            (one_day_ago,),
        )

    cv_to_id_fetch: dict[int, tuple[int, int]] = {
        e["comicvine_id"]: (e["id"], e["last_cv_fetch"]) for e in cursor
    }
    if not cv_to_id_fetch:
        return

    # Update volumes
    cv = ComicVine()
    volume_datas = filtered_volume_datas = run(
        cv.fetch_volumes(tuple(cv_to_id_fetch.keys()))
    )

    if not volume_id and allow_skipping:
        cv_id_to_issue_count: dict[int, int] = dict(
            cursor.execute(
                """
            SELECT v.comicvine_id, COUNT(i.id)
            FROM volumes v
            LEFT JOIN issues i
            ON v.id = i.volume_id
            WHERE v.last_cv_fetch <= ?
            GROUP BY i.volume_id;
            """,
                (one_day_ago,),
            )
        )

        filtered_volume_datas = [
            v
            for v in volume_datas
            if cv_id_to_issue_count[v["comicvine_id"]] != v["issue_count"]
            or cv_to_id_fetch[v["comicvine_id"]][1] <= five_days_ago
        ]

    cursor.executemany(
        """
        UPDATE volumes
        SET
            title = :title,
            alt_title = :alt_title,
            year = :year,
            publisher = :publisher,
            volume_number = :volume_number,
            description = :description,
            site_url = :site_url,
            cover = :cover,
            last_cv_fetch = :last_cv_fetch
        WHERE id = :id;
        """,
        (
            {
                "title": vd["title"],
                "alt_title": (vd["aliases"] or [None])[0],
                "year": vd["year"],
                "publisher": vd["publisher"],
                "volume_number": vd["volume_number"],
                "description": vd["description"],
                "site_url": vd["site_url"],
                "cover": vd["cover"],
                "last_cv_fetch": one_day_ago + SECONDS_IN_DAY,
                "id": cv_to_id_fetch[vd["comicvine_id"]][0],
            }
            for vd in volume_datas
        ),
    )
    commit()

    # Update issues
    issue_datas = run(
        cv.fetch_issues(tuple(vd["comicvine_id"] for vd in filtered_volume_datas))
    )
    monitor_issues_volume_ids: set[int] = set(
        first_of_subarrays(
            cursor.execute("SELECT id FROM volumes WHERE monitor_new_issues = 1;")
        )
    )
    cursor.executemany(
        """
        INSERT INTO issues(
            volume_id,
            comicvine_id,
            issue_number,
            calculated_issue_number,
            title,
            date,
            description,
            monitored
        ) VALUES (
            :volume_id, :comicvine_id, :issue_number, :calculated_issue_number,
            :title, :date, :description, :monitored
        )
        ON CONFLICT(comicvine_id) DO
        UPDATE
        SET
            issue_number = :issue_number,
            calculated_issue_number = :calculated_issue_number,
            title = :title,
            date = :date,
            description = :description;
        """,
        (
            {
                "volume_id": cv_to_id_fetch[isd["volume_id"]][0],
                "comicvine_id": isd["comicvine_id"],
                "issue_number": isd["issue_number"],
                "calculated_issue_number": isd["calculated_issue_number"] or 0.0,
                "title": isd["title"],
                "date": isd["date"],
                "description": isd["description"],
                "monitored": cv_to_id_fetch[isd["volume_id"]][0]
                in monitor_issues_volume_ids,
            }
            for isd in issue_datas
        ),
    )

    commit()

    # Delete issues from DB that aren't found in CV response
    volume_issues_fetched: dict[int, set[int]] = {}
    for isd in issue_datas:
        (
            volume_issues_fetched.setdefault(isd["volume_id"], set()).add(
                isd["comicvine_id"]
            )
        )

    for vd in filtered_volume_datas:
        if (
            len(volume_issues_fetched.get(vd["comicvine_id"]) or tuple())
            != vd["issue_count"]
        ):
            continue

        # All issues of the volume have been fetched (not guaranteed because of
        # CV API rate limit).
        issue_cv_to_id = dict(
            cursor.execute(
                """
            SELECT i.comicvine_id, i.id
            FROM issues i
            INNER JOIN volumes v
            ON i.volume_id = v.id
            WHERE v.comicvine_id = ?;
            """,
                (vd["comicvine_id"],),
            ).fetchall()
        )
        for issue_cv, issue_id in issue_cv_to_id.items():
            if issue_cv not in volume_issues_fetched[vd["comicvine_id"]]:
                # Issue is in database but not in CV, so remove
                LOGGER.debug(f"Deleting issue with ID {issue_id} and CV ID {issue_cv}")
                Issue(issue_id).delete()
                commit()

    # Refresh Special Version
    cursor.executemany(
        """
        UPDATE volumes
        SET special_version = :special_version
        WHERE id = :id AND special_version_locked = 0;
        """,
        tuple(
            {
                "special_version": determine_special_version(
                    cv_to_id_fetch[vd["comicvine_id"]][0]
                ),
                "id": cv_to_id_fetch[vd["comicvine_id"]][0],
            }
            for vd in volume_datas
        ),
    )
    commit()

    # Scan for files
    if volume_id:
        scan_files(volume_id, update_websocket=update_websocket)

    else:
        v_ids = [(v[0], [], False, update_websocket) for v in cv_to_id_fetch.values()]
        total_count = len(v_ids)

        if not total_count:
            return

        with PortablePool(
            max_processes=min(Constants.DB_MAX_CONCURRENT_CONNECTIONS, total_count)
        ) as pool:
            if update_websocket:
                ws = WebSocket()
                for idx, _ in enumerate(pool.istarmap_unordered(scan_files, v_ids)):
                    ws.update_task_status(
                        message=f"Scanned files for volume {idx + 1}/{total_count}"
                    )

            else:
                pool.starmap(scan_files, v_ids)

        FilesDB.delete_unmatched_files()

    return


def delete_issue_file(file_id: int) -> None:
    """Delete a file from the library and remove it from the filesystem.

    Args:
        file_id (int): The ID of the file to delete.
    """
    file_data = FilesDB.fetch(file_id=file_id)[0]
    volume_id = FilesDB.volume_of_file(file_data["filepath"])
    unmonitor_deleted_issues = Settings().sv.unmonitor_deleted_issues and volume_id

    if volume_id:
        vf = Library().get_volume(volume_id).vd.folder
        delete_file_folder(file_data["filepath"])
        delete_empty_parent_folders(dirname(file_data["filepath"]), vf)
    else:
        delete_file_folder(file_data["filepath"])

    cursor = get_db()
    not_downloaded_issues: list[int] = first_of_subarrays(
        cursor.execute(
            """
        WITH matched_file_counts AS (
            SELECT
                issue_id,
                COUNT(file_id) AS matched_file_count
            FROM issues_files
            WHERE issue_id IN (
                SELECT issue_id
                FROM issues_files
                WHERE file_id = ?
            )
            GROUP BY issue_id
        )
        SELECT issue_id
        FROM matched_file_counts
        WHERE matched_file_count = 1
        """,
            (file_id,),
        )
    )

    if volume_id:
        WebSocket().update_downloaded_status(
            volume_id, not_downloaded_issues=not_downloaded_issues
        )

    if unmonitor_deleted_issues:
        cursor.executemany(
            "UPDATE issues SET monitored = 0 WHERE id = ?;",
            ((i,) for i in not_downloaded_issues),
        )

    FilesDB.delete_file(file_id)

    return
