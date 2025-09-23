"""
All download implementations.
"""

from __future__ import annotations

import builtins
from base64 import b64encode
from os.path import basename, join, sep, splitext
from re import IGNORECASE, compile
from threading import Event, Thread
from time import perf_counter
from typing import TYPE_CHECKING, Any, cast, final
from urllib.parse import unquote_plus

import requests
from bs4 import BeautifulSoup, Tag
from requests import RequestException

from backend.base.custom_exceptions import (
    ClientNotWorking,
    DownloadLimitReached,
    IssueNotFound,
    LinkBroken,
)
from backend.base.definitions import (
    BlocklistReason,
    Constants,
    CredentialSource,
    Download,
    DownloadSource,
    DownloadState,
    DownloadType,
    ExternalDownload,
    ExternalDownloadClient,
    GeneralFileData,
)
from backend.base.helpers import Session, first_of_range, get_torrent_info
from backend.base.logging import LOGGER
from backend.implementations.credentials import Credentials
from backend.implementations.direct_clients.mega import Mega, MegaABC, MegaFolder
from backend.implementations.external_clients import ExternalClients
from backend.implementations.naming import generate_issue_name
from backend.implementations.torrent_clients.qBittorrent import qBittorrent
from backend.implementations.volumes import Issue, Volume
from backend.internals.db import get_db
from backend.internals.server import WebSocket
from backend.internals.settings import Settings

if TYPE_CHECKING:
    from requests import Response


# autopep8: off
file_extension_regex = compile(r"(?<=\.|\/)[\w\d]{2,4}(?=$|;|\s|\")", IGNORECASE)
file_name_regex = compile(
    r"filename(?:=\"|\*=UTF-8\'\')(.*?)\.[a-z]{2,4}\"?$", IGNORECASE
)
extract_mediafire_regex = compile(
    r"window.location.href\s?=\s?\'https://download\d+\.mediafire.com/.*?(?=\')",
    IGNORECASE,
)
DOWNLOAD_CHUNK_SIZE = 4194304  # 4MB Chunks
MEDIAFIRE_FOLDER_LINK = "https://www.mediafire.com/api/1.5/file/zip.php"
WETRANSFER_API_LINK = "https://wetransfer.com/api/v4/transfers/{transfer_id}/download"
# autopep8: on


# region Base Direct Download
class BaseDirectDownload(Download):
    __r: Any | None
    _id: int | None

    @property
    def attempts(self) -> int:
        return self._attempts

    @attempts.setter
    def attempts(self, value: int) -> None:
        self._attempts = value
        return

    @property
    def id(self) -> int | None:
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        self._id = value
        return

    @property
    def volume_id(self) -> int:
        return self._volume_id

    @property
    def issue_id(self) -> int | None:
        return self._issue_id

    @property
    def covered_issues(self) -> float | tuple[float, float] | None:
        return self._covered_issues

    @property
    def web_link(self) -> str | None:
        return self._web_link

    @property
    def web_title(self) -> str | None:
        return self._web_title

    @property
    def web_sub_title(self) -> str | None:
        return self._web_sub_title

    @property
    def download_link(self) -> str:
        return self._download_link

    @property
    def pure_link(self) -> str:
        return self._pure_link

    @property
    def source_type(self) -> DownloadSource:
        return self._source_type

    @property
    def source_name(self) -> str:
        return self._source_name

    @property
    def files(self) -> list[str]:
        return self._files

    @files.setter
    def files(self, value: list[str]) -> None:
        self._files = value
        return

    @property
    def filename_body(self) -> str:
        return self._filename_body

    @property
    def title(self) -> str:
        return self._title

    @property
    def size(self) -> int:
        return self._size

    @property
    def state(self) -> DownloadState:
        return self._state

    @state.setter
    def state(self, value: DownloadState) -> None:
        self._state = value
        return

    @property
    def progress(self) -> float:
        return self._progress

    @property
    def speed(self) -> float:
        return self._speed

    _download_thread: Thread | None

    @property
    def download_thread(self) -> Thread | None:
        return self._download_thread

    @download_thread.setter
    def download_thread(self, value: Thread) -> None:
        self._download_thread = value
        return

    @property
    def download_folder(self) -> str:
        return self._download_folder

    @property
    def releaser(self) -> str | None:
        return self._releaser

    @property
    def scan_type(self) -> str | None:
        return self._scan_type

    @property
    def resolution(self) -> str | None:
        return self._resolution

    @property
    def dpi(self) -> str | None:
        return self._dpi

    @property
    def extension(self) -> str | None:
        return self._extension

    def __init__(
        self,
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
        extension: str | None = None,
        forced_match: bool = False,
    ) -> None:
        LOGGER.debug("Creating download: %s", download_link)

        settings = Settings().sv
        volume = Volume(volume_id)

        self._attempts = 0
        self.__r = None
        self._download_link = download_link
        self._volume_id = volume_id
        self._issue_id = None
        self._covered_issues = covered_issues
        self._source_type = source_type
        self._source_name = source_name
        self._web_link = web_link
        self._web_title = web_title
        self._web_sub_title = web_sub_title

        self._id = None
        self._state = DownloadState.QUEUED_STATE
        self._progress = 0.0
        self._speed = 0.0
        self._download_thread = None
        self._download_folder = settings.download_folder

        self._releaser = releaser
        self._scan_type = scan_type
        self._resolution = resolution
        self._dpi = dpi
        self._extension = extension

        self._ssn = Session()

        # Create and fetch pure link to extract last info
        # This can fail if the link is broken, so do before other
        # intensive tasks to save time (no need to do intensive tasks when
        # link is broken).
        try:
            self._pure_link = self._convert_to_pure_link()
            with self._fetch_pure_link() as response:
                response.raise_for_status()
                self._ssn.close()

        except RequestException as e:
            if (
                e.response is not None
                and e.response.url.startswith(Constants.PIXELDRAIN_API_URL)
                and e.response.status_code == 403
            ):
                # Pixeldrain rate limit because of hotlinking
                raise DownloadLimitReached(DownloadSource.PIXELDRAIN)

            raise LinkBroken(BlocklistReason.LINK_BROKEN)

        self._size = int(response.headers.get("Content-Length", -1))

        self._filename_body = ""
        try:
            if isinstance(covered_issues, float):
                self._issue_id = Issue.from_volume_and_calc_number(
                    volume_id, covered_issues
                ).id

            if settings.rename_downloaded_files:
                self._filename_body = generate_issue_name(
                    volume_id,
                    volume.get_data().special_version,
                    covered_issues,
                    cast(
                        GeneralFileData,
                        {
                            "releaser": releaser,
                            "scan_type": scan_type,
                            "resolution": resolution,
                            "dpi": dpi,
                        },
                    ),
                )

        except IssueNotFound as e:
            if not forced_match:
                raise e

        if not self._filename_body:
            self._filename_body = self._extract_default_filename_body(response)

        self._title = basename(self._filename_body)
        self._files = [self._build_filename(response)]
        return

    def _convert_to_pure_link(self) -> str:
        return self.download_link

    def _fetch_pure_link(self) -> Response:
        return self._ssn.get(self.pure_link, stream=True)

    def _extract_default_filename_body(self, response: Response | None) -> str:
        if response and response.headers.get("Content-Disposition"):
            file_result = file_name_regex.search(
                response.headers["Content-Disposition"]
            )
            if file_result:
                return unquote_plus(file_result.group(1))

        return splitext(unquote_plus(self.pure_link.split("/")[-1].split("?")[0]))[0]

    def _extract_extension(self, response: Response | None) -> str:
        if self.extension is not None:
            return f".{self.extension}"

        if not response:
            return ""

        match = file_extension_regex.findall(
            " ".join(
                (
                    response.headers.get("Content-Disposition", ""),
                    response.headers.get("Content-Type", ""),
                    response.url,
                )
            )
        )
        if match:
            return "." + match[0]
        return ""

    def _build_filename(self, response: Response | None) -> str:
        extension = self._extract_extension(response)
        return join(
            self._download_folder, "_".join(self._filename_body.split(sep)) + extension
        )

    def run(self) -> None:
        self._state = DownloadState.DOWNLOADING_STATE
        size_downloaded = 0
        ws = WebSocket()
        ws.update_queue_status(self)

        with self._fetch_pure_link() as r, open(self.files[0], "wb") as f:
            self.__r = r
            start_time = perf_counter()
            try:
                for chunk in r.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if self.state in (
                        DownloadState.CANCELED_STATE,
                        DownloadState.SHUTDOWN_STATE,
                    ):
                        break

                    f.write(chunk)

                    # Update progress
                    chunk_size = len(chunk)
                    size_downloaded += chunk_size
                    self._speed = round(chunk_size / (perf_counter() - start_time), 2)
                    if self.size == -1:
                        # No file size so progress is amount downloaded
                        self._progress = size_downloaded
                    else:
                        self._progress = round(size_downloaded / self.size * 100, 2)

                    start_time = perf_counter()
                    ws.update_queue_status(self)

            except RequestException:
                self._state = DownloadState.FAILED_STATE

            finally:
                self.__r = None

        if self.size != -1 and size_downloaded != self.size:
            # Download completed, but downloaded size is not equal
            # to reported size of file
            self._state = DownloadState.FAILED_STATE

        self._attempts = self._attempts + 1
        return

    def stop(self, state: DownloadState = DownloadState.CANCELED_STATE) -> None:
        self._state = state

        LOGGER.info(f"Bypassing retries for download {self._id}")
        self._attempts = 50

        if self.__r and self.__r.raw._fp and not isinstance(self.__r.raw._fp, str):
            self.__r.raw._fp.fp.raw._sock.shutdown(2)

        return

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "volume_id": self._volume_id,
            "issue_id": self._issue_id,
            "web_link": self._web_link,
            "web_title": self._web_title,
            "web_sub_title": self._web_sub_title,
            "download_link": self._download_link,
            "pure_link": self._pure_link,
            "source_type": self._source_type.value,
            "source_name": self._source_name,
            "type": self.identifier,
            "file": self._files[0],
            "title": self._title,
            "download_folder": self._download_folder,
            "size": self._size,
            "status": self._state.value,
            "progress": self._progress,
            "speed": self._speed,
        }


# region Direct
@final
class DirectDownload(BaseDirectDownload):
    "For downloading a file directly from a link"

    identifier: str = "direct"


# region MediaFire
@final
class MediaFireDownload(BaseDirectDownload):
    "For downloading a MediaFire file"

    identifier: str = "mf"

    def _convert_to_pure_link(self) -> str:
        r = self._ssn.get(self.download_link, stream=True)
        result = extract_mediafire_regex.search(r.text)
        if result:
            return result.group(0).split("'")[-1]

        soup = BeautifulSoup(r.text, "html.parser")
        button = soup.find("a", {"id": "downloadButton"})
        if isinstance(button, Tag):
            return first_of_range(button["href"])

        # Link is not broken and not a folder
        # but we still can't find the download button...
        raise LinkBroken(BlocklistReason.LINK_BROKEN)


# region MediaFire Folder
@final
class MediaFireFolderDownload(BaseDirectDownload):
    "For downloading a MediaFire folder (for MF file, use MediaFireDownload)"

    identifier: str = "mf_folder"

    def _convert_to_pure_link(self) -> str:
        return self.download_link.split("/folder/")[1].split("/")[0]

    def _fetch_pure_link(self) -> Response:
        return self._ssn.post(
            MEDIAFIRE_FOLDER_LINK,
            files={
                "keys": (None, self.pure_link),
                "meta_only": (None, "no"),
                "allow_large_download": (None, "yes"),
                "response_format": (None, "json"),
            },
            stream=True,
        )


# region WeTransfer
@final
class WeTransferDownload(BaseDirectDownload):
    "For downloading a file or folder from WeTransfer"

    identifier: str = "wt"

    def _convert_to_pure_link(self) -> str:
        transfer_id, security_hash = self.download_link.split("/")[-2:]
        r = self._ssn.post(
            WETRANSFER_API_LINK.format(transfer_id=transfer_id),
            json={"intent": "entire_transfer", "security_hash": security_hash},
            headers={"x-requested-with": "XMLHttpRequest"},
        )
        if not r.ok:
            raise LinkBroken(BlocklistReason.LINK_BROKEN)

        direct_link = r.json().get("direct_link")

        if not direct_link:
            raise LinkBroken(BlocklistReason.LINK_BROKEN)

        return direct_link


# region PixelDrain
class PixelDrainDownload(BaseDirectDownload):
    "For downloading a file from PixelDrain"

    identifier: str = "pd"

    @staticmethod
    def login(api_key: str) -> int:
        LOGGER.debug("Logging into Pixeldrain with user api key")
        with Session() as session:
            enc_api_key = b64encode(f":{api_key}".encode()).decode()

            try:
                r = session.get(
                    Constants.PIXELDRAIN_API_URL + "/user",
                    headers={"Authorization": "Basic " + enc_api_key},
                )
                if r.status_code == 401:
                    return -1

            except RequestException:
                raise ClientNotWorking(
                    "An unexpected error occured when making contact with Pixeldrain"
                )

            response = r.json()
            if (response["subscription"]["type"] or "free").lower() == "free":
                # Free account, so fetch standard rate limits
                limits = session.get(
                    Constants.PIXELDRAIN_API_URL + "/misc/rate_limits",
                    headers={"Authorization": "Basic " + enc_api_key},
                ).json()

                transfer_limit_used = limits["transfer_limit_used"]
                transfer_limit = limits["transfer_limit"]

            else:
                # Paid account, so grab transfer limits from user data
                transfer_limit_used = response["monthly_transfer_used"]
                transfer_limit = response["monthly_transfer_cap"]
                if transfer_limit == -1:
                    transfer_limit = float("inf")

        LOGGER.debug(
            f"Pixeldrain account transfer state: {transfer_limit_used}/{transfer_limit}"
        )
        return int(transfer_limit_used < transfer_limit)

    def _convert_to_pure_link(self) -> str:
        self._api_key = None
        self._first_fetch = True
        download_id = self.download_link.rstrip("/").split("/")[-1]
        return Constants.PIXELDRAIN_API_URL + "/file/" + download_id

    def _fetch_pure_link(self) -> Response:
        if self._first_fetch:
            cred = Credentials()
            for pd_cred in cred.get_from_source(CredentialSource.PIXELDRAIN):
                if self.login(pd_cred.api_key or "") == 1:
                    # Key works and has not reached limit
                    self._api_key = pd_cred.api_key
                    break
            self._first_fetch = False

        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = (
                "Basic " + b64encode(f":{self._api_key}".encode()).decode()
            )

        return self._ssn.get(self.pure_link, headers=headers, stream=True)


# region PixelDrain Folder
@final
class PixelDrainFolderDownload(PixelDrainDownload):
    "For downloading a PixelDrain folder (for PD file, use PixelDrainDownload)"

    identifier: str = "pd_folder"

    def _convert_to_pure_link(self) -> str:
        self._api_key = None
        self._first_fetch = True
        download_id = self.download_link.rstrip("/").split("/")[-1]
        "https://pixeldrain.com/api/list/{download_id}/zip"
        return Constants.PIXELDRAIN_API_URL + "/list/" + download_id + "/zip"


# region Mega
class MegaDownload(BaseDirectDownload):
    "For downloading a file via Mega"

    identifier: str = "mega"

    _mega_class: builtins.type[MegaABC] = Mega

    @property
    def size(self) -> int:
        return self._mega.size

    @property
    def progress(self) -> float:
        return self._mega.progress

    @property
    def speed(self) -> float:
        return self._mega.speed

    @property
    def _size(self) -> int:
        return self._mega.size

    @_size.setter
    def _size(self, value: int) -> None:
        self._mega.size = value
        return

    @property
    def _progress(self) -> float:
        return self._mega.progress

    @_progress.setter
    def _progress(self, value: float) -> None:
        self._mega.progress = value
        return

    @property
    def _speed(self) -> float:
        return self._mega.speed

    @_speed.setter
    def _speed(self, value: float) -> None:
        self._mega.speed = value
        return

    @property
    def _pure_link(self) -> str:
        return self._mega.pure_link

    @_pure_link.setter
    def _pure_link(self, value: str) -> None:
        self._mega.pure_link = value
        return

    def __init__(
        self,
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
        extension: str | None = None,
        forced_match: bool = False,
    ) -> None:
        LOGGER.debug("Creating mega download: %s", download_link)

        settings = Settings().sv
        volume = Volume(volume_id)

        self._attempts = 0

        self._download_link = download_link
        self._volume_id = volume_id
        self._issue_id = None
        self._covered_issues = covered_issues
        self._source_type = source_type
        self._source_name = source_name
        self._web_link = web_link
        self._web_title = web_title
        self._web_sub_title = web_sub_title

        self._id = None
        self._state = DownloadState.QUEUED_STATE
        self._download_thread = None
        self._download_folder = settings.download_folder

        self._releaser = releaser
        self._scan_type = scan_type
        self._resolution = resolution
        self._dpi = dpi
        self._extension = extension

        try:
            self._mega = self._mega_class(download_link)
        except ClientNotWorking:
            raise LinkBroken(BlocklistReason.LINK_BROKEN)

        self._filename_body = ""
        try:
            if isinstance(covered_issues, float):
                self._issue_id = Issue.from_volume_and_calc_number(
                    volume_id, covered_issues
                ).id

            if settings.rename_downloaded_files:
                self._filename_body = generate_issue_name(
                    volume_id, volume.get_data().special_version, covered_issues
                )

        except IssueNotFound as e:
            if not forced_match:
                raise e

        if not self._filename_body:
            self._filename_body = self._extract_default_filename_body(response=None)

        self._title = basename(self._filename_body)
        self._files = [self._build_filename(response=None)]
        return

    def _extract_default_filename_body(self, response: Response | None) -> str:
        return splitext(self._mega.mega_filename)[0]

    def _extract_extension(self, response: Response | None) -> str:
        return splitext(self._mega.mega_filename)[1]

    def run(self) -> None:
        self._state = DownloadState.DOWNLOADING_STATE
        ws = WebSocket()
        try:
            self._mega.download(self.files[0], lambda: ws.update_queue_status(self))

        except ClientNotWorking:
            self._state = DownloadState.FAILED_STATE

        return

    def stop(self, state: DownloadState = DownloadState.CANCELED_STATE) -> None:
        self._state = state
        self._mega.stop()
        return


@final
class MegaFolderDownload(MegaDownload):
    "For downloading a Mega folder (for Mega file, use MegaDownload)"

    identifier: str = "mega_folder"

    _mega_class = MegaFolder


# region Torrent
@final
class TorrentDownload(ExternalDownload, BaseDirectDownload):
    identifier: str = "torrent"

    @property
    def external_client(self) -> ExternalDownloadClient:
        return self._external_client

    @external_client.setter
    def external_client(self, value: ExternalDownloadClient) -> None:
        self._external_client = value
        return

    @property
    def external_id(self) -> str | None:
        return self._external_id

    @property
    def sleep_event(self) -> Event:
        return self._sleep_event

    def __init__(
        self,
        download_link: str,
        volume_id: int,
        covered_issues: float | tuple[float, float] | None,
        source_type: DownloadSource,
        source_name: str,
        web_link: str | None,
        web_title: str | None,
        web_sub_title: str | None,
        forced_match: bool = False,
        external_client: ExternalDownloadClient | None = None,
        external_id: str | None = None,
        filename: str | None = None,
        releaser: str | None = None,
        scan_type: str | None = None,
        resolution: str | None = None,
        dpi: str | None = None,
        extension: str | None = None,
    ) -> None:
        LOGGER.debug("Creating download: %s", download_link)

        settings = Settings().sv

        self._download_link = self._pure_link = download_link
        self._volume_id = volume_id
        self._issue_id = None
        self._covered_issues = covered_issues
        self._source_type = source_type
        self._source_name = source_name
        self._web_link = web_link
        self._web_title = web_title
        self._web_sub_title = web_sub_title
        self._external_id = external_id
        self._filename = filename

        self._id = None
        self._state = DownloadState.QUEUED_STATE
        self._progress = 0.0
        self._speed = 0.0
        self._size = -1
        self._download_thread = None
        self._download_folder = settings.download_folder
        self._sleep_event = Event()

        self._releaser = releaser
        self._scan_type = scan_type
        self._resolution = resolution
        self._dpi = dpi
        self._extension = extension

        self._original_files: list[str] = []
        if external_client:
            self._external_client = external_client
            if external_id and isinstance(self._external_client, qBittorrent):
                self._external_client.torrent_hashes[external_id] = None
        else:
            self._external_client = ExternalClients.get_least_used_client(
                DownloadType.TORRENT
            )

        try:
            if isinstance(covered_issues, float):
                self._issue_id = Issue.from_volume_and_calc_number(
                    volume_id, covered_issues
                ).id

        except IssueNotFound as e:
            if not forced_match:
                raise e

        # Find name of torrent as that becomes folder that media is
        # downloaded in
        if download_link.startswith("magnet"):
            try:
                response = Session().post(
                    "https://magnet2torrent.com/upload/", data={"magnet": download_link}
                )
                response.raise_for_status()
                if response.headers.get("Content-Type") != "application/x-bittorrent":
                    raise RequestException

            except RequestException:
                raise LinkBroken(BlocklistReason.LINK_BROKEN)

            torrent_name = get_torrent_info(response.content)[b"name"].decode()
        else:
            torrent_name = get_torrent_info(requests.get(download_link).content)[
                b"name"
            ].decode()

        self._filename_body = ""
        if settings.rename_downloaded_files:
            try:
                self._filename_body = generate_issue_name(
                    volume_id,
                    Volume(volume_id).get_data().special_version,
                    covered_issues,
                )

            except IssueNotFound as e:
                if not forced_match:
                    raise e

        if not self._filename_body:
            self._filename_body = splitext(torrent_name)[0]

        self._title = basename(self._filename_body)
        self._files = [join(self._download_folder, torrent_name)]
        return

    def run(self) -> None:
        if not self.external_id:
            self._external_id = self.external_client.add_download(
                self.download_link,
                self._download_folder
                if not self._filename
                else join(self._download_folder, self._filename),
                self.title,
                self._filename,
            )
            if self.id:
                get_db().execute(
                    "UPDATE download_queue SET external_id = ? WHERE id = ?;",
                    (self.external_id, self.id),
                )
        return

    def update_status(self) -> None:
        if not self.external_id:
            return

        torrent_status = self.external_client.get_download(self.external_id)
        if not torrent_status:
            if torrent_status is None:
                self._state = DownloadState.CANCELED_STATE
            return

        self._progress = torrent_status["progress"]
        self._speed = torrent_status["speed"]
        self._size = torrent_status["size"]
        if self.state not in (
            DownloadState.CANCELED_STATE,
            DownloadState.SHUTDOWN_STATE,
        ):
            self._state = torrent_status["state"]

        return

    def remove_from_client(self, delete_files: bool) -> None:
        if not self.external_id:
            return

        self.external_client.delete_download(self.external_id, delete_files)
        return

    def stop(self, state: DownloadState = DownloadState.CANCELED_STATE) -> None:
        self._state = state
        self._sleep_event.set()
        return

    def as_dict(self) -> dict[str, Any]:
        return {
            **super().as_dict(),
            "client": self.external_client.id if self._external_client else None,
        }
