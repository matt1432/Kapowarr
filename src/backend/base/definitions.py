"""
Definitions of types, constants, enums, typed dicts, dataclasses
and abstract classes.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
from threading import Event, Thread
from typing import (
    TYPE_CHECKING,
    Any,
    TypedDict,
)

import requests

if TYPE_CHECKING:
    from backend.base.helpers import AsyncSession


# region Constants
FETCHED_CONSTANTS = json.loads(
    requests.get(
        "https://raw.githubusercontent.com/matt1432/Kapowarr/refs/heads/main/constants.json"
    ).text
)


class Constants:
    SUB_PROCESS_TIMEOUT = 20.0  # seconds
    "Seconds to wait after interrupt until subprocess is killed"

    HOSTING_THREADS = 10
    "Amount of threads for the webserver"

    HOSTING_TIMER_DURATION = 60.0  # seconds
    """
    Seconds to wait after restarting from hosting changes
    until they are reverted
    """

    DB_FOLDER = ("db",)
    "Subfolder of application folder to put database in"

    DB_NAME = "Kapowarr.db"
    "Name of database file itself"

    CV_CACHE_NAME = "cv_cache.sqlite"
    "Name of database file itself"

    DB_TIMEOUT = 10.0  # seconds
    "Seconds to wait on database command before timing out"

    DB_MAX_CONCURRENT_CONNECTIONS = 32
    "Maximum allowed database connections to be open at the same time"

    LOGGER_NAME = "Kapowarr"
    "Name of the logger that is used"

    LOGGER_FILENAME = "Kapowarr.log"
    "Filename that the logs are put in"

    PASSWORD_REPLACEMENT: str = "********"
    "What passwords are replaced with when shared as a string"

    MAX_FILENAME_LENGTH = 255
    "The maximum amount of characters that a filename is allowed to be"

    ARCHIVE_EXTRACT_FOLDER = ".archive_extract"
    "The subfolder to extract archives into temporarily"

    ZIP_MIN_MOD_TIME = 315619200  # epoch
    "The minimum modification time that a file inside a zip should have"

    DEFAULT_USERAGENT = "Kapowarr"
    "The user agent to use when making web requests"

    BROWSER_USERAGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    "The user agent to use when making web requests as a browser"

    REQUEST_TIMEOUT = 30  # seconds
    "The default timeout for network requests"

    TOTAL_RETRIES = 5
    "The amount of times to try a network connection before giving up"

    BACKOFF_FACTOR_RETRIES = 1
    "Backoff factor for waiting in-between retries"

    STATUS_FORCELIST_RETRIES = (500, 502, 503, 504)
    "The HTTP status codes for which a retry should be done"

    CV_SITE_URL = "https://comicvine.gamespot.com"
    "The site URL of ComicVine"

    CV_API_URL = "https://comicvine.gamespot.com/api"
    "The base URL of the ComicVine API"

    CV_BRAKE_TIME = 10.0  # seconds
    "Average amount of seconds between requests to the CV API"

    LIBGEN_SITE_URL = FETCHED_CONSTANTS["libgen_site_url"]
    """
    The site URL of Libgen+. It is fetched from the latest commit of this
    project's github repository to ensure users always have a working URL
    """

    GC_SITE_URL = "https://getcomics.org"
    "The site URL of GetComics"

    GC_SOURCE_TERM = "GetComics"
    "The name used for GetComics as a download source"

    MEGA_API_URL = "https://eu.api.mega.co.nz/cs"
    "The base URL of the Mega API"

    PIXELDRAIN_API_URL = "https://pixeldrain.com/api"
    "The base URL of the Pixeldrain API"

    FS_API_BASE = "/v1"
    "The base endpoint of the FlareSolverr API"

    CF_CHALLENGE_HEADER = ("cf-mitigated", "challenge")
    """
    The key and value of the header supplied by CloudFlare
    when a challenge is presented
    """

    TORRENT_UPDATE_INTERVAL = 5  # seconds
    "The interval in seconds between status updates from external clients"

    TORRENT_TAG = "kapowarr"
    "The tag to give to downloads at external clients"


class FileConstants:
    IMAGE_EXTENSIONS = (
        ".png",
        ".jpeg",
        ".jpg",
        ".webp",
        ".gif",
        ".PNG",
        ".JPEG",
        ".JPG",
        ".WEBP",
        ".GIF",
    )
    "Image extensions, both lowercase and uppercase, with dot-prefix"

    CONTAINER_EXTENSIONS = (
        ".cbz",
        ".zip",
        ".rar",
        ".cbr",
        ".tar.gz",
        ".7zip",
        ".7z",
        ".cb7",
        ".cbt",
        ".epub",
        ".pdf",
    )
    "Archive/container extensions, both lowercase and uppercase, with dot-prefix"

    METADATA_EXTENSIONS = (".xml", ".json", ".XML", ".JSON")
    "Metadata file extensions, both lowercase and uppercase, with dot-prefix"

    METADATA_FILES = {
        "cvinfo.xml",
        "comicinfo.xml",
        "series.json",
        "metadata.json",
    }
    "Filenames of metadata files, only lowercase"

    ARCHIVE_MAGIC_BYTES = {
        b"\x50\x4b\x03\x04": "zip",  # ZIP
        b"Rar!\x1a\x07\x00": "rar",  # RAR 4.x
        b"Rar!\x1a\x07\x01\x00": "rar",  # RAR 5.x
        b"\x37\x7a\xbc\xaf\x27\x1c": "7z",  # 7z
    }
    """
    Maps magic bytes of archive files to their lowercase extension
    without dot-prefix
    """

    CB_TO_ARCHIVE_EXTENSIONS = {"cbz": "zip", "cbr": "rar", "cb7": "7z"}
    """
    Maps lowercase cb* extensions to their lowercase archive extension,
    both without dot-prefix
    """


CONTENT_EXTENSIONS = (
    *FileConstants.IMAGE_EXTENSIONS,
    *FileConstants.CONTAINER_EXTENSIONS,
)
"Media file extensions, both lowercase and uppercase, with dot-prefix"


SCANNABLE_EXTENSIONS = (*CONTENT_EXTENSIONS, *FileConstants.METADATA_EXTENSIONS)
"Media and metadata file extensions, both lowercase and uppercase, with dot-prefix"


class CharConstants:
    ALPHABET = (
        "a",
        "b",
        "c",
        "d",
        "e",
        "f",
        "g",
        "h",
        "i",
        "j",
        "k",
        "l",
        "m",
        "n",
        "o",
        "p",
        "q",
        "r",
        "s",
        "t",
        "u",
        "v",
        "w",
        "x",
        "y",
        "z",
    )
    "A tuple of all lowercase letters in the alphabet"

    DIGITS = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
    "A set of the numbers 0-9 in string form"

    ROMAN_DIGITS = {
        "i": 1,
        "ii": 2,
        "iii": 3,
        "iv": 4,
        "v": 5,
        "vi": 6,
        "vii": 7,
        "viii": 8,
        "ix": 9,
        "x": 10,
    }
    "A map of lowercase roman numerals 1-10 to their int equivalent"


# region Enums
class BaseEnum(Enum):
    def __eq__(self, other: object) -> bool:
        return self.value == other

    def __hash__(self) -> int:
        return id(self.value)


class StartType(BaseEnum):
    "The reason for or cause of starting up"

    STARTUP = 130
    "Normal startup"

    RESTART = 131
    "A normal restart"

    RESTART_HOSTING_CHANGES = 132
    "A restart because changes to the hosting settings were made"


class SeedingHandling(BaseEnum):
    "How to handle downloads that completed but still have to seed"

    COMPLETE = "complete"
    "Let download fully complete (finish seeding) and then move all files"

    COPY = "copy"
    """
    Copy the files while the download is seeding,
    and once done delete original files
    """


class DateType(BaseEnum):
    "The type of comic date used in the database"

    COVER_DATE = "cover_date"
    STORE_DATE = "store_date"


class BlocklistReasonID(BaseEnum):
    "The ID assosiated with the reason for putting a link on the blocklist"

    LINK_BROKEN = 1
    SOURCE_NOT_SUPPORTED = 2
    NO_WORKING_LINKS = 3
    ADDED_BY_USER = 4


class BlocklistReason(BaseEnum):
    "The reason for putting a link on the blocklist"

    LINK_BROKEN = "Link broken"
    SOURCE_NOT_SUPPORTED = "Source not supported"
    NO_WORKING_LINKS = "No supported or working links"
    ADDED_BY_USER = "Added by user"


class MatchRejections(BaseEnum):
    BLOCKLISTED = "Link is blocklisted"
    ANNUAL = "Annual conflict"
    TITLE = "Titles don't match"
    VOLUME_NUMBER = "Volume numbers don't match"
    ISSUE_NUMBER = "Issue numbers don't match"
    SPECIAL_VERSION = "Special version conflict"
    YEAR = "Year doesn't match"


class SpecialVersion(BaseEnum):
    "The type of volume"

    TPB = "tpb"

    ONE_SHOT = "one-shot"

    HARD_COVER = "hard-cover"

    OMNIBUS = "omnibus"

    VOLUME_AS_ISSUE = "volume-as-issue"
    "Volume where each issue is named `Volume N`"

    COVER = "cover"
    "Image file is cover of either issue or volume. Overrules over SV's."

    METADATA = "metadata"
    "Metadata file"

    NORMAL = None
    "Normal volume, so not a special version"


SV_TO_SHORT_TERM: dict[SpecialVersion, str] = dict(
    (
        (SpecialVersion.HARD_COVER, "HC"),
        (SpecialVersion.ONE_SHOT, "OS"),
        (SpecialVersion.TPB, "TPB"),
        (SpecialVersion.OMNIBUS, "Omnibus"),
        (SpecialVersion.COVER, "Cover"),
    )
)
"""
A mapping from a SpecialVersion to a short string representing it.
E.g. `SpecialVersion.HARD_COVER` -> `HC`
"""

SV_TO_FULL_TERM: dict[SpecialVersion, str] = dict(
    (
        (SpecialVersion.HARD_COVER, "Hard-Cover"),
        (SpecialVersion.ONE_SHOT, "One-Shot"),
        (SpecialVersion.TPB, "TPB"),
        (SpecialVersion.OMNIBUS, "Omnibus"),
        (SpecialVersion.COVER, "Cover"),
    )
)
"""
A mapping from a SpecialVersion to a full string representing it.
E.g. `SpecialVersion.HARD_COVER` -> `Hard-Cover`
"""


class LibrarySorting(BaseEnum):
    """
    The way to order the library, where the key value is the value of the
    `ORDER BY ...` SQL statement
    """

    TITLE = "title, year, volume_number"
    YEAR = "year, title, volume_number"
    VOLUME_NUMBER = "volume_number, title, year"
    RECENTLY_ADDED = "id DESC, title, year, volume_number"
    PUBLISHER = "publisher, title, year, volume_number"
    WANTED = (
        "issues_downloaded_monitored >= issue_count_monitored, "
        "title, year, volume_number"
    )
    RECENTLY_RELEASED = (
        "(SELECT MAX(date) FROM vol_issues) DESC, title, year, volume_number"
    )


class LibraryFilter(BaseEnum):
    """
    The filter to apply to the library, where the key value is the entire
    `WHERE ...` SQL statement
    """

    WANTED = "WHERE issues_downloaded_monitored < issue_count_monitored"
    MONITORED = "WHERE monitored = 1"


class DownloadState(BaseEnum):
    QUEUED_STATE = "queued"
    PAUSED_STATE = "paused"
    DOWNLOADING_STATE = "downloading"
    SEEDING_STATE = "seeding"
    IMPORTING_STATE = "importing"

    FAILED_STATE = "failed"
    "Download was unsuccessful"
    CANCELED_STATE = "canceled"
    "Download was removed from queue"
    SHUTDOWN_STATE = "shutting down"
    "Download was stopped because Kapowarr is shutting down"


class SocketEvent(BaseEnum):
    "The websocket event"

    TASK_ADDED = "task_added"
    TASK_STATUS = "task_status"
    TASK_ENDED = "task_ended"

    QUEUE_ADDED = "queue_added"
    "A download is added to the queue"
    QUEUE_STATUS = "queue_status"
    "A status update on a download in the queue"
    QUEUE_ENDED = "queue_ended"
    "A download has finished in the queue"

    VOLUME_UPDATED = "volume_updated"
    ISSUE_UPDATED = "issue_updated"

    VOLUME_DELETED = "volume_deleted"
    ISSUE_DELETED = "issue_deleted"

    MASS_EDITOR_STATUS = "mass_editor_status"
    "The progress of a mass editor action"

    DOWNLOADED_STATUS = "downloaded_status"
    "A change in what issues are marked as downloaded and which aren't"


class FailReason(BaseEnum):
    "The reason a download failed to be added to the queue"

    BROKEN = "GetComics page unavailable"
    NO_WORKING_LINKS = "No working download links on page"
    LIMIT_REACHED = "Download limit reached for service"
    NO_MATCHES = "No links found that match to volume and are not blocklisted"


class GeneralFileType(BaseEnum):
    METADATA = "metadata"
    COVER = "cover"


class GCDownloadSource(BaseEnum):
    "Download sources offered on a GetComics webpage"

    MEGA = "Mega"
    MEDIAFIRE = "MediaFire"
    WETRANSFER = "WeTransfer"
    PIXELDRAIN = "Pixeldrain"
    GETCOMICS = "GetComics"
    "A direct download link straight from their own servers"
    GETCOMICS_TORRENT = "GetComics (torrent)"
    "A torrent magnet link directly on the webpage"


GC_DOWNLOAD_SOURCE_TERMS: dict[GCDownloadSource, tuple[str, ...]] = dict(
    (
        (GCDownloadSource.MEGA, ("mega", "mega link")),
        (GCDownloadSource.MEDIAFIRE, ("mediafire", "mediafire link")),
        (
            GCDownloadSource.WETRANSFER,
            (
                "wetransfer",
                "we transfer",
                "wetransfer link",
                "we transfer link",
            ),
        ),
        (
            GCDownloadSource.PIXELDRAIN,
            (
                "pixeldrain",
                "pixel drain",
                "pixeldrain link",
                "pixel drain link",
            ),
        ),
        (
            GCDownloadSource.GETCOMICS,
            (
                "getcomics",
                "download now",
                "main download",
                "main server",
                "main link",
                "mirror download",
                "mirror server",
                "mirror link",
                "link 1",
                "link 2",
            ),
        ),
        (
            GCDownloadSource.GETCOMICS_TORRENT,
            (
                "getcomics (torrent)",
                "torrent",
                "torrent link",
                "magnet",
                "magnet link",
            ),
        ),
    )
)
"""
GCDownloadSource to strings that can be found in the button text for the
service on the GC page
"""


# Future proofing. In the future, there'll be sources like 'torrent' and
# 'usenet'. In part of the code, we want access to all download sources,
# and in the other part we only want the GC services. So in preparation
# of the torrent and usenet sources coming, we're already making the
# distinction here.
class DownloadSource(BaseEnum):
    "All possible download sources"

    MEGA = "Mega"
    MEDIAFIRE = "MediaFire"
    WETRANSFER = "WeTransfer"
    PIXELDRAIN = "Pixeldrain"
    GETCOMICS = "GetComics"
    "A direct download link straight from their own servers"
    GETCOMICS_TORRENT = "GetComics (torrent)"
    "A torrent magnet link directly on the webpage"
    LIBGENPLUS = "Libgen+"


class MonitorScheme(BaseEnum):
    ALL = "all"
    MISSING = "missing"
    NONE = "none"


class CredentialSource(BaseEnum):
    MEGA = "mega"
    PIXELDRAIN = "pixeldrain"


class DownloadType(BaseEnum):
    "The download protocol (download type)"

    DIRECT = 1
    TORRENT = 2


QUERY_FORMATS: dict[str, tuple[str, ...]] = {
    "TPB": (
        "{title} Vol. {volume_number} ({year}) TPB",
        "{title} ({year}) TPB",
        "{title} Vol. {volume_number} TPB",
        "{title} Vol. {volume_number}",
        "{title}",
    ),
    "VAI": ("{title} ({year})", "{title}"),
    "Volume": (
        "{title} Vol. {volume_number} ({year})",
        "{title} ({year})",
        "{title} Vol. {volume_number}",
        "{title}",
    ),
    "Issue": (
        "{title} #{issue_number} ({year})",
        "{title} Vol. {volume_number} #{issue_number}",
        "{title} #{issue_number}",
        "{title}",
    ),
}
"""
Volume SV to query formats used when searching
"""


# region TypedDicts
class ApiResponse(TypedDict):
    result: Any
    error: str | None
    code: int


class FileExtraInfo(TypedDict):
    releaser: str
    scan_type: str
    resolution: str
    dpi: str


class FilenameData(TypedDict):
    series: str
    year: int | None
    volume_number: int | tuple[int, int] | None
    special_version: str | None
    issue_number: float | tuple[float, float] | None
    annual: bool
    is_metadata_file: bool
    is_image_file: bool


class RemoteMappingData(TypedDict):
    id: int
    external_download_client_id: int
    remote_path: str
    local_path: str


class SearchResultData(FilenameData):
    link: str
    display_title: str
    source: str
    filesize: int
    pages: int
    releaser: str | None
    scan_type: str | None
    resolution: str | None
    dpi: str | None
    extension: str | None
    comics_id: int | None
    md5: str | None


class SearchResultMatchData(TypedDict):
    match: bool
    match_rejections: list[str]  # list[MatchRejections]


class MatchedSearchResultData(
    SearchResultMatchData, SearchResultData, total=False
):
    _issue_number: float | tuple[float, float]
    rank: list[int]


class VolumeMetadata(TypedDict):
    comicvine_id: int
    title: str
    year: int | None
    volume_number: int
    cover_link: str
    cover: bytes | None
    description: str
    site_url: str
    aliases: list[str]
    publisher: str | None
    issue_count: int
    translated: bool
    already_added: int | None
    issues: list[IssueMetadata] | None
    folder_name: str


class IssueMetadata(TypedDict):
    comicvine_id: int
    volume_id: int
    issue_number: str
    calculated_issue_number: float
    title: str | None
    date: date | None
    description: str


class CVFileMapping(TypedDict):
    id: int
    filepath: str


class DownloadGroup(TypedDict):
    web_sub_title: str
    info: FilenameData
    links: dict[GCDownloadSource, list[str]]


class ClientTestResult(TypedDict):
    success: bool
    description: None | str


class SizeData(TypedDict):
    total: int
    used: int
    free: int


class FileData(FileExtraInfo):
    id: int
    filepath: str
    size: int


class GeneralFileData(FileData):
    file_type: str


# region Dataclasses
@dataclass
class BlocklistEntry:
    id: int
    volume_id: int | None
    issue_id: int | None

    web_link: str | None
    web_title: str | None
    web_sub_title: str | None

    download_link: str | None
    source: str | None

    reason: BlocklistReason
    added_at: int

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["reason"] = self.reason.value
        return result


@dataclass
class RootFolder:
    id: int
    folder: str
    size: SizeData

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BaseNamingKeys:
    series_name: str
    clean_series_name: str
    volume_number: str
    comicvine_id: int
    year: int | None
    publisher: str | None


@dataclass
class SVNamingKeys(BaseNamingKeys):
    special_version: str | None
    releaser: str | None
    scan_type: str | None
    resolution: str | None
    dpi: str | None


@dataclass
class IssueNamingKeys(SVNamingKeys):
    issue_comicvine_id: int
    issue_number: str | None
    issue_title: str | None
    issue_release_date: str | None
    issue_release_year: int | None


class IssueFileData(FileData, FilenameData):
    pass


@dataclass
class IssueData:
    id: int
    volume_id: int
    comicvine_id: int
    issue_number: str
    calculated_issue_number: float
    title: str | None
    date: str | None
    description: str | None
    monitored: bool
    files: list[IssueFileData]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VolumeData:
    id: int
    comicvine_id: int
    libgen_series_id: str | None
    title: str
    alt_title: str | None
    year: int
    publisher: str
    volume_number: int
    description: str
    site_url: str
    monitored: bool
    monitor_new_issues: bool
    root_folder: int
    folder: str
    custom_folder: bool
    special_version: SpecialVersion
    special_version_locked: bool
    last_cv_fetch: int


@dataclass
class CredentialData:
    id: int
    source: CredentialSource
    username: str | None
    email: str | None
    password: str | None
    api_key: str | None

    def __post_init__(self) -> None:
        if isinstance(self.username, str):
            self.username = self.username.strip() or None
        if isinstance(self.email, str):
            self.email = self.email.strip() or None
        if isinstance(self.password, str):
            self.password = self.password.strip() or None
        if isinstance(self.api_key, str):
            self.api_key = self.api_key.strip() or None
        return

    def as_dict(self) -> dict[str, Any]:
        "Note: Will replace password with a string of stars"
        result = asdict(self)

        result["source"] = self.source.value

        if result["password"] is not None:
            result["password"] = Constants.PASSWORD_REPLACEMENT

        return result


# region Abstract Classes
class KapowarrException(Exception, ABC):
    "An exception specific to Kapowarr"

    @property
    @abstractmethod
    def api_response(self) -> ApiResponse: ...


class DBMigrator(ABC):
    start_version: int

    @abstractmethod
    def run(self) -> None: ...


class MassEditorAction(ABC):
    identifier: str
    "The string used in the API to refer to the action"

    def __init__(self, volume_ids: list[int]) -> None:
        """Prepare a mass editor action.

        Args:
            volume_ids (List[int]): The volume IDs to work on.
        """
        self.volume_ids = volume_ids
        return

    @abstractmethod
    def run(self, **kwargs: Any) -> None:
        """Run the mass editor action."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(action={self.identifier}; ids={self.volume_ids}); {id(self)}>"


class FileConverter(ABC):
    source_format: str
    target_format: str

    @staticmethod
    @abstractmethod
    def convert(file: str) -> list[str]:
        """Convert a file from `source_format` to `target_format`.

        Args:
            file (str): Filepath to the source file, should be in `source_format`.

        Returns:
            List[str]: The resulting files or directories, in `target_format`.
        """
        ...


class SearchSource(ABC):
    def __init__(self, query: str) -> None:
        """Prepare the search source.

        Args:
            query (str): The query to search for.
        """
        self.query = query
        return

    @abstractmethod
    async def search(self, session: AsyncSession) -> list[SearchResultData]:
        """Search for the query.

        Args:
            session (AsyncSession): The session to use for the search.

        Returns:
            List[SearchResultData]: The search results.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(query={self.query}); {id(self)}>"


class ExternalDownloadClient(ABC):
    client_type: str
    "The name of the external client (e.g. 'qBittorrent')"

    download_type: DownloadType
    "The protocol it uses to download (e.g. a torrent)"

    required_tokens: Sequence[str]
    """
    The keys the client needs or could need for operation
    (mostly whether it's username + password or api_token)
    """

    @property
    @abstractmethod
    def id(self) -> int: ...

    @property
    @abstractmethod
    def title(self) -> str: ...

    @property
    @abstractmethod
    def base_url(self) -> str: ...

    @property
    @abstractmethod
    def username(self) -> str | None: ...

    @property
    @abstractmethod
    def password(self) -> str | None: ...

    @property
    @abstractmethod
    def api_token(self) -> str | None: ...

    @abstractmethod
    def __init__(self, client_id: int) -> None:
        """Create a connection with a client.

        Args:
            client_id (int): The ID of the client.
        """
        ...

    @abstractmethod
    def get_client_data(self) -> dict[str, Any]:
        """Get info about the client.

        Returns:
            Dict[str, Any]: The info about the client.
        """
        ...

    @abstractmethod
    def update_client(self, data: Mapping[str, Any]) -> None:
        """Edit the client.

        Args:
            data (Mapping[str, Any]): The keys and their new values for
            the client settings.

        Raises:
            ClientDownloading: There is a download using the client.
            ExternalClientNotWorking: Failed to connect to the client.
            KeyNotFound: A required key was not found.
            InvalidKeyValue: One of the parameters has an invalid argument.
        """
        ...

    @abstractmethod
    def delete_client(self) -> None:
        """Delete the client.

        Raises:
            ClientDownloading: There is a download using the client.
        """
        ...

    @abstractmethod
    def add_download(
        self,
        download_link: str,
        target_folder: str,
        download_name: str | None,
        filename: str | None = None,
    ) -> str:
        """Add a download to the client.

        Args:
            download_link (str): The link to the download (e.g. magnet link).
            target_folder (str): The folder to download in.
            download_name (Union[str, None]): The name of the downloaded folder
            or file. Set to `None` to keep original name.

        Raises:
            ExternalClientNotWorking: Can't connect to client.

        Returns:
            str: The ID/hash of the entry in the download client.
        """
        ...

    @abstractmethod
    def get_download(self, download_id: str) -> dict[str, Any] | None:
        """Get the information/status of a download.

        Args:
            download_id (str): The ID/hash of the download to get info of.

        Raises:
            ExternalClientNotWorking: Can't connect to client.

        Returns:
            Union[dict[str, Any], None]: The status of the download,
            empty dict if download is not found
            and `None` if client deleted the download.
        """
        ...

    @abstractmethod
    def delete_download(self, download_id: str, delete_files: bool) -> None:
        """Remove the download from the client.

        Raises:
            ExternalClientNotWorking: Can't connect to client.

        Args:
            download_id (str): The ID/hash of the download to delete.
            delete_files (bool): Whether to delete the downloaded files.
        """
        ...

    @staticmethod
    @abstractmethod
    def test(
        base_url: str,
        username: str | None,
        password: str | None,
        api_token: str | None,
    ) -> str | None:
        """Check if a download client is working.

        Args:
            base_url (str): The base url on which the client is running.
            username (Union[str, None]): The username to access the client, if set.
            password (Union[str, None]): The password to access the client, if set.
            api_token (Union[str, None]): The API token to access the client, if set.

        Returns:
            Union[str, None]: If it's a fail, the reason for failing. If it's
            a success, `None`.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}; title={self.title}); {id(self)}>"


class Download(ABC):
    identifier: str
    "An identifier for the specific download implementation (e.g. 'mf_folder')"

    @property
    @abstractmethod
    def attempts(self) -> int:
        "The amount of times this download has been attempted. Used for Libgen+"
        ...

    @attempts.setter
    @abstractmethod
    def attempts(self, value: int) -> None: ...

    @property
    @abstractmethod
    def id(self) -> int | None: ...

    @id.setter
    @abstractmethod
    def id(self, value: int) -> None: ...

    @property
    @abstractmethod
    def volume_id(self) -> int: ...

    @property
    @abstractmethod
    def issue_id(self) -> int | None: ...

    @property
    @abstractmethod
    def covered_issues(self) -> float | tuple[float, float] | None: ...

    @property
    @abstractmethod
    def web_link(self) -> str | None:
        "Link to webpage for download"
        ...

    @property
    @abstractmethod
    def web_title(self) -> str | None:
        "Title of webpage (or release) for download"
        ...

    @property
    @abstractmethod
    def web_sub_title(self) -> str | None:
        "Title of sub-section that download falls under (e.g. GC group name)"
        ...

    @property
    @abstractmethod
    def download_link(self) -> str:
        "The link to the download or service page (e.g. link to MF page)"
        ...

    @property
    @abstractmethod
    def pure_link(self) -> str:
        "The pure link to download from (e.g. pixeldrain API link or MF folder ID)"
        ...

    @property
    @abstractmethod
    def source_type(self) -> DownloadSource: ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """
        The display name of the source. E.g. `source_type` is torrent,
        so `source_name` is indexer name.
        """
        ...

    @property
    @abstractmethod
    def files(self) -> list[str]:
        "List of folders/files that were 'produced' by this download"
        ...

    @files.setter
    @abstractmethod
    def files(self, value: list[str]) -> None: ...

    @property
    @abstractmethod
    def filename_body(self) -> str:
        """
        The body of the file/folder name that the downloaded file(s) should
        be named as at their (almost) final destination. Only filename, and
        without extension. E.g. `Iron-Man Volume 02 Issue 003`
        """
        ...

    @property
    @abstractmethod
    def download_folder(self) -> str: ...

    @property
    @abstractmethod
    def title(self) -> str:
        "Display title of download"
        ...

    @property
    @abstractmethod
    def size(self) -> int:
        "Total size of download in bytes, or `-1` if unknown"
        ...

    @property
    @abstractmethod
    def state(self) -> DownloadState: ...

    @state.setter
    @abstractmethod
    def state(self, value: DownloadState) -> None: ...

    @property
    @abstractmethod
    def progress(self) -> float:
        "Progress of download, as a value between `0.0` and `100.0`"
        ...

    @property
    @abstractmethod
    def speed(self) -> float:
        "Download speed, in bytes per second"
        ...

    @property
    @abstractmethod
    def download_thread(self) -> Thread | None: ...

    @download_thread.setter
    @abstractmethod
    def download_thread(self, value: Thread) -> None: ...

    @property
    @abstractmethod
    def releaser(self) -> str | None: ...

    @property
    @abstractmethod
    def scan_type(self) -> str | None: ...

    @property
    @abstractmethod
    def resolution(self) -> str | None: ...

    @property
    @abstractmethod
    def dpi(self) -> str | None: ...

    @abstractmethod
    def __init__(
        self,
        *,
        download_link: str,
        volume_id: int,
        covered_issues: float | tuple[float, float] | None,
        source_type: DownloadSource,
        source_name: str,
        web_link: str | None,
        web_title: str | None,
        web_sub_title: str | None,
        releaser: str | None = None,
        scan_type: str | None = None,
        resolution: str | None = None,
        dpi: str | None = None,
        forced_match: bool = False,
    ) -> None:
        """Prepare the download.

        Args:
            download_link (str): The link to the download.
                Could be direct download link, mega link, magnet link, etc.

            volume_id (int): The ID of the volume that the download is for.

            covered_issues (Union[float, Tuple[float, float], None]):
            The calculated issue number (range) that the download covers,
            or None if download is for special version.

            source_type (DownloadSource): The source type of the download.

            source_name (str): The display name of the source.
            E.g. indexer name.

            web_link (Union[str, None]): Link to webpage for download.

            web_title (Union[str, None]): Title of webpage (or release) for download.

            web_sub_title (Union[str, None]): Title of sub-section that download
            falls under (e.g. GC group name).

            forced_match (bool, optional): Whether the download was forcefully
            added by the user. Try renaming (if setting says so), but use
            default name if file doesn't match to issues.
                Defaults to False.

        Raises:
            LinkBroken: The link doesn't work.

            IssueNotFound: The download refers to issues that don't exist in the
            volume, and download is not forced.
        """
        ...

    @abstractmethod
    def run(self) -> None:
        """
        Start the download.

        Raises:
            DownloadLimitReached: At the source that is downloaded from,
            we've reached a rate limit.
        """
        ...

    @abstractmethod
    def stop(self, state: DownloadState = DownloadState.CANCELED_STATE) -> None:
        """Interrupt the download.

        Args:
            state (DownloadState, optional): The state to set for the download.
                Defaults to DownloadState.CANCELED_STATE.
        """
        ...

    @abstractmethod
    def as_dict(self) -> dict[str, Any]:
        """Get a dict representing the download.

        Returns:
            Dict[str, Any]: The dict with all information.
        """
        ...

    def get_file_extra_info(self) -> FileExtraInfo:
        return FileExtraInfo(
            releaser=self.releaser or "",
            scan_type=self.scan_type or "",
            resolution=self.resolution or "",
            dpi=self.dpi or "",
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(download_link={self.download_link}; file={self.files[0]}; state={self.state.value}); {id(self)}>"


class ExternalDownload(Download):
    @property
    @abstractmethod
    def external_client(self) -> ExternalDownloadClient: ...

    @external_client.setter
    @abstractmethod
    def external_client(self, value: ExternalDownloadClient) -> None: ...

    @property
    @abstractmethod
    def external_id(self) -> str | None:
        "The ID/hash of the download in the external client."
        ...

    @property
    @abstractmethod
    def sleep_event(self) -> Event:
        """
        A `threading.Event` to use inside the download thread
        for sleeping in between status checks
        """
        ...

    @abstractmethod
    def __init__(
        self,
        *,
        download_link: str,
        volume_id: int,
        covered_issues: float | tuple[float, float] | None,
        source_type: DownloadSource,
        source_name: str,
        web_link: str | None,
        web_title: str | None,
        web_sub_title: str | None,
        releaser: str | None = None,
        scan_type: str | None = None,
        resolution: str | None = None,
        dpi: str | None = None,
        forced_match: bool = False,
        external_client: ExternalDownloadClient | None = None,
        external_id: str | None = None,
    ) -> None:
        """Prepare the download.

        Args:
            download_link (str): The link to the download.
                Could be direct download link, mega link, magnet link, etc.

            volume_id (int): The ID of the volume that the download is for.

            covered_issues (Union[float, Tuple[float, float], None]):
            The calculated issue number (range) that the download covers,
            or None if download is for special version.

            source_type (DownloadSource): The source type of the download.

            source_name (str): The display name of the source.
            E.g. indexer name.

            web_link (Union[str, None]): Link to webpage for download.

            web_title (Union[str, None]): Title of webpage (or release) for download.

            web_sub_title (Union[str, None]): Title of sub-section that download
            falls under (e.g. GC group name).

            forced_match (bool, optional): Whether the download was forcefully
            added by the user. Try renaming (if setting says so), but use
            default name if file doesn't match to issues.
                Defaults to False.

            external_client (Union[ExternalDownloadClient, None], optional):
            Force an external client instead of letting the download choose one.
                Defaults to None.

        Raises:
            LinkBroken: The link doesn't work

            IssueNotFound: The download refers to issues that don't exist in the
            volume, and download is not forced.
        """
        ...

    @abstractmethod
    def update_status(self) -> None:
        """
        Update the various variables about the state/progress
        of the external download
        """
        ...

    @abstractmethod
    def remove_from_client(self, delete_files: bool) -> None:
        """Remove the download from the external client.

        Args:
            delete_files (bool): Delete downloaded files.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(download_link={self.download_link}; file={self.files[0]}; state={self.state.value}); {id(self)}>"
