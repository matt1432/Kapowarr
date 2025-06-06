"""
All custom exceptions are defined here

Note: Not all CE's inherit from CustomException.
"""

from typing import Any, TypedDict

from backend.base.definitions import (
    BlocklistReason,
    BlocklistReasonID,
    DownloadSource,
    FailReason,
)
from backend.base.logging import LOGGER


class ApiResponse(TypedDict):
    error: str
    result: dict[str, str | int | None]
    code: int


class CustomException(Exception):
    def __init__(self, e: Any = None) -> None:
        LOGGER.warning(self.__doc__)
        super().__init__(e)
        return


class FolderNotFound(CustomException):
    """Folder not found"""

    api_response = {"error": "FolderNotFound", "result": {}, "code": 404}


class RootFolderNotFound(CustomException):
    """Rootfolder with given ID not found"""

    api_response = {"error": "RootFolderNotFound", "result": {}, "code": 404}


class RootFolderInUse(CustomException):
    """A root folder with the given ID is requested to be deleted but is used by a volume"""

    api_response = {"error": "RootFolderInUse", "result": {}, "code": 400}


class RootFolderInvalid(CustomException):
    """The root folder is a parent or child of an existing root folder, which is not allowed"""

    api_response = {"error": "RootFolderInvalid", "result": {}, "code": 400}


class VolumeNotFound(CustomException):
    """The volume with the given (comicvine-) key was not found"""

    api_response = {"error": "VolumeNotFound", "result": {}, "code": 404}


class VolumeNotMatched(CustomException):
    """Volume not matched with ComicVine database"""

    api_response = {"error": "VolumeNotMatched", "result": {}, "code": 400}


class CVRateLimitReached(CustomException):
    """ComicVine API rate limit reached"""

    api_response = {"error": "CVRateLimitReached", "result": {}, "code": 509}


class VolumeAlreadyAdded(CustomException):
    """The volume that is desired to be added is already added"""

    api_response = {"error": "VolumeAlreadyAdded", "result": {}, "code": 400}


class VolumeDownloadedFor(Exception):
    """The volume is desired to be deleted but there is a download for it going"""

    def __init__(self, volume_id: int):
        self.volume_id = volume_id
        super().__init__(self.volume_id)
        LOGGER.warning(
            f"Deleting volume failed because there is a download for the volume: {self.volume_id}"
        )
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "VolumeDownloadedFor",
            "result": {"volume_id": self.volume_id},
            "code": 400,
        }


class TaskForVolumeRunning(Exception):
    """The volume is desired to be deleted but there is a task running for it"""

    def __init__(self, volume_id: int):
        self.volume_id = volume_id
        super().__init__(self.volume_id)
        LOGGER.warning(
            f"Deleting volume failed because there is a task for the volume: {self.volume_id}"
        )
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "TaskForVolumeRunning",
            "result": {"volume_id": self.volume_id},
            "code": 400,
        }


class IssueNotFound(CustomException):
    """Issue with given ID not found"""

    api_response = {"error": "IssueNotFound", "result": {}, "code": 404}


class TaskNotFound(CustomException):
    """Task with given ID not found"""

    api_response = {"error": "TaskNotFound", "result": {}, "code": 404}


class TaskNotDeletable(CustomException):
    """The task could not be deleted because it's the first in the queue"""

    api_response = {"error": "TaskNotDeletable", "result": {}, "code": 400}


class DownloadNotFound(CustomException):
    """Download with given ID not found"""

    api_response = {"error": "DownloadNotFound", "result": {}, "code": 404}


class BlocklistEntryNotFound(CustomException):
    """Blocklist entry with given ID not found"""

    api_response = {"error": "BlocklistEntryNotFound", "result": {}, "code": 404}


class InvalidComicVineApiKey(CustomException):
    """No Comic Vine API key is set or it's invalid"""

    api_response = {"error": "InvalidComicVineApiKey", "result": {}, "code": 400}


class LinkBroken(Exception):
    """Download link doesn't work"""

    def __init__(self, reason: BlocklistReason):
        self.reason = reason
        self.reason_text = reason.value
        self.reason_id = BlocklistReasonID[reason.name].value
        super().__init__(self.reason_id)
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "LinkBroken",
            "result": {"reason_text": self.reason_text, "reason_id": self.reason_id},
            "code": 400,
        }


class FailedGCPage(Exception):
    """Something failed processing the GC page"""

    def __init__(self, reason: FailReason):
        self.reason = reason
        super().__init__(self.reason.value)
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "FailedGCPage",
            "result": {"reason_text": self.reason.value},
            "code": 400,
        }


class InvalidSettingKey(Exception):
    """The setting key is unknown"""

    def __init__(self, key: str = ""):
        self.key = key
        super().__init__(self.key)
        LOGGER.warning(f"No setting matched the given key: {key}")
        return

    @property
    def api_response(self) -> ApiResponse:
        return {"error": "InvalidSettingKey", "result": {"key": self.key}, "code": 400}


class InvalidSettingValue(Exception):
    """The setting value is invalid"""

    def __init__(self, key: str = "", value: Any = ""):
        self.key = key
        self.value = value
        super().__init__(self.key)
        LOGGER.warning(f"The value for this setting is invalid: {key}: {value}")
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "InvalidSettingValue",
            "result": {"key": self.key, "value": self.value},
            "code": 400,
        }


class InvalidSettingModification(Exception):
    """The setting is not allowed to be changed this way"""

    def __init__(self, key: str = "", instead: str = ""):
        self.key = key
        self.instead = instead
        super().__init__(key)
        LOGGER.warning(
            f"This setting is not allowed to be changed this way: {key}."
            + f" Instead: {instead}"
        )
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "InvalidSettingModification",
            "result": {"key": self.key, "instead": self.instead},
            "code": 400,
        }


class KeyNotFound(Exception):
    """A key that is required to be given in the api request was not found"""

    def __init__(self, key: str = ""):
        self.key = key
        super().__init__(self.key)
        if key != "password":
            LOGGER.warning(
                "This key was not found in the API request,"
                + f" eventhough it's required: {key}"
            )
        return

    @property
    def api_response(self) -> ApiResponse:
        return {"error": "KeyNotFound", "result": {"key": self.key}, "code": 400}


class InvalidKeyValue(Exception):
    """A key given in the api request has an invalid value"""

    def __init__(self, key: str = "", value: Any = ""):
        self.key = key
        self.value = value
        super().__init__(self.key)
        if value not in ("undefined", "null"):
            LOGGER.warning(
                "This key in the API request has an invalid value: "
                + f"{key} = {value}"
            )
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "InvalidKeyValue",
            "result": {"key": self.key, "value": self.value},
            "code": 400,
        }


class CredentialNotFound(CustomException):
    """Credential with given ID not found"""

    api_response = {"error": "CredentialNotFound", "result": {}, "code": 404}


class CredentialInvalid(Exception):
    """A credential is incorrect (can't login with it)"""

    def __init__(self, description: str) -> None:
        self.desc = description
        LOGGER.warning(f"Failed to login with credentials with reason: {self.desc}")
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "CredentialInvalid",
            "result": {"description": self.desc},
            "code": 400,
        }


class DownloadLimitReached(Exception):
    """The download limit (download quota) of the source is reached"""

    def __init__(self, source: DownloadSource) -> None:
        self.source = source
        LOGGER.warning(
            f"Download source {source.value} has reached it's download limit"
        )
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "DownloadLimitReached",
            "result": {"source": self.source.value},
            "code": 509,
        }


class DownloadUnmovable(CustomException):
    """The position of the download in the queue can not be changed"""

    api_response = {"error": "DownloadUnmovable", "result": {}, "code": 400}


class ExternalClientNotFound(CustomException):
    """External client with given ID not found"""

    api_response = {"error": "ExternalClientNotFound", "result": {}, "code": 404}


class ClientDownloading(Exception):
    """
    The external client is desired to be deleted
    but there is a download using it
    """

    def __init__(self, client_id: int):
        self.client_id = client_id
        super().__init__(self.client_id)
        LOGGER.warning(
            "Deleting external client failed because there is "
            + f"a download using it: {self.client_id}"
        )
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "ClientDownloading",
            "result": {"client_id": self.client_id},
            "code": 400,
        }


class ClientNotWorking(Exception):
    """The client is not working"""

    def __init__(self, description: str = "") -> None:
        self.desc = description
        super().__init__(self.desc)
        LOGGER.warning(f"Client failed with description: {self.desc}")
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "ClientNotWorking",
            "result": {"description": self.desc},
            "code": 400,
        }


class ExternalClientNotWorking(Exception):
    """External client is not working"""

    def __init__(self, description: str | None = None) -> None:
        self.desc = description
        super().__init__(self.desc)
        LOGGER.warning(
            f"Failed to connect to external client for the following reason: {self.desc}"
        )
        return

    @property
    def api_response(self) -> ApiResponse:
        return {
            "error": "ExternalClientNotWorking",
            "result": {"description": self.desc},
            "code": 400,
        }


class LogFileNotFound(CustomException):
    """No log file was found"""

    api_response = {"error": "LogFileNotFound", "result": {}, "code": 404}


class FileNotFound(CustomException):
    """File with given ID not found"""

    api_response = {"error": "FileNotFound", "result": {}, "code": 404}
