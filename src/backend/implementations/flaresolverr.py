from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from requests import RequestException

from backend.base.definitions import Constants
from backend.base.helpers import Session
from backend.base.logging import LOGGER
from backend.internals.settings import Settings

if TYPE_CHECKING:
    from backend.base.helpers import AsyncSession


class FlareSolverr:
    cookie_mapping: dict[str, dict[str, str]] = {}
    ua_mapping: dict[str, str] = {}

    def __init__(self) -> None:
        self.base_url = Settings().sv.flaresolverr_base_url or None
        return

    @staticmethod
    def test_flaresolverr(base_url: str) -> bool:
        """Test the connection to a FlareSolverr instance.

        Args:
            base_url (str): The base URL of the FlareSolverr instance. Supply
                base URL without API extension.

        Returns:
            bool: Whether the connection was successful.
        """
        with Session() as session:
            try:
                result = session.get(f"{base_url}/health")

                if result.status_code != 200:
                    return False

                result = result.json()
                if result.get("status") != "ok":
                    return False

            except RequestException:
                return False
        return True

    def is_enabled(self) -> bool:
        """Check if FlareSolverr is enabled.

        Returns:
            bool: Whether FlareSolverr is enabled.
        """
        return self.base_url is not None

    def get_ua_cookies(self, url: str) -> tuple[str, dict[str, str]]:
        """Get the user agent and cookies for a certain URL. The UA and cookies
        can be cleared by CF, so use them to avoid challenges. In case the URL
        is not CF protected, or hasn't explicitly been cleared yet, then the
        default UA is returned and no cookie definitions.

        Args:
            url (str): The URL to get the UA and cookies for.

        Returns:
            Tuple[str, Dict[str, str]]: First element is the UA, or default
                UA. Second element is a mapping of any extra cookies.
        """
        return (
            self.ua_mapping.get(url, Constants.DEFAULT_USERAGENT),
            self.cookie_mapping.get(url, {}),
        )

    def handle_cf_block(
        self, url: str, headers: Mapping[str, str]
    ) -> None | dict[str, Any]:
        """Let FS handle a URL to aquire cleared cookies and UA. These become
        available using `get_ua_cookies()` after this method completes.

        Args:
            url (str): The URL to clear.
            headers (Mapping[str, str]): The response headers from the
                (possibly) blocked request.

        Returns:
            Union[None, Dict[str, Any]]: None if FlareSolverr wasn't needed or
                couldn't solve the problem, or a dictionary with the FlareSolverr
                response.
        """
        if (
            headers.get(Constants.CF_CHALLENGE_HEADER[0])
            != Constants.CF_CHALLENGE_HEADER[1]
        ):
            # Request not failed because of CF block
            return

        if not self.base_url:
            LOGGER.warning(
                "Request blocked by CloudFlare and FlareSolverr not setup"
            )
            return

        with Session() as session:
            session_id = session.post(
                self.base_url + Constants.FS_API_BASE,
                json={"cmd": "sessions.create"},
                headers={"Content-Type": "application/json"},
            ).json()["session"]

            result = session.post(
                self.base_url + Constants.FS_API_BASE,
                json={"cmd": "request.get", "session": session_id, "url": url},
                headers={"Content-Type": "application/json"},
            ).json()["solution"]

            session.post(
                self.base_url + Constants.FS_API_BASE,
                json={"cmd": "sessions.destroy", "session": session_id},
                headers={"Content-Type": "application/json"},
            )

            self.ua_mapping[url] = result["userAgent"]
            self.cookie_mapping[url] = {
                cookie["name"]: cookie["value"] for cookie in result["cookies"]
            }

        return result

    async def handle_cf_block_async(
        self, session: AsyncSession, url: str, headers: Mapping[str, str]
    ) -> None | dict[str, Any]:
        """Let FS handle a URL to aquire cleared cookies and UA. These become
        available using `get_ua_cookies()` after this method completes.

        Args:
            session (AsyncSession): The session to make the request to FS with.
            url (str): The URL to clear.
            headers (Mapping[str, str]): The response headers from the
                (possibly) blocked request.

        Returns:
            Union[None, Dict[str, Any]]: None if FlareSolverr wasn't needed or
                couldn't solve the problem, or a dictionary with the FlareSolverr
                response.
        """
        if (
            headers.get(Constants.CF_CHALLENGE_HEADER[0])
            != Constants.CF_CHALLENGE_HEADER[1]
        ):
            # Request not failed because of CF block
            return

        if not self.base_url:
            LOGGER.warning(
                "Request blocked by CloudFlare and FlareSolverr not setup"
            )
            return

        session_id = (
            await (
                await session.post(
                    self.base_url + Constants.FS_API_BASE,
                    json={"cmd": "sessions.create"},
                    headers={"Content-Type": "application/json"},
                )
            ).json()
        )["session"]

        result = (
            await (
                await session.post(
                    self.base_url + Constants.FS_API_BASE,
                    json={
                        "cmd": "request.get",
                        "session": session_id,
                        "url": url,
                    },
                    headers={"Content-Type": "application/json"},
                )
            ).json()
        )["solution"]

        await session.post(
            self.base_url + Constants.FS_API_BASE,
            json={"cmd": "sessions.destroy", "session": session_id},
            headers={"Content-Type": "application/json"},
        )

        self.ua_mapping[url] = result["userAgent"]
        self.cookie_mapping[url] = {
            cookie["name"]: cookie["value"] for cookie in result["cookies"]
        }

        return result
