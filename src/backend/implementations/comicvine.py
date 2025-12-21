"""
Search for volumes/issues and fetch metadata for them on ComicVine
"""

from asyncio import gather, run, sleep
from collections.abc import Sequence
from datetime import date
from os.path import dirname, join
from pathlib import Path
from re import IGNORECASE, compile
from typing import Any

from aiohttp.client_exceptions import ClientError
from bs4 import BeautifulSoup, Tag
from simyan.comicvine import (
    AuthenticationError,
    BasicIssue,
    BasicVolume,
    Comicvine,
    ComicvineResource,
    Issue,
    ServiceError,
    SQLiteCache,
    Volume,
)

from backend.base.custom_exceptions import (
    CVRateLimitReached,
    InvalidComicVineApiKey,
    VolumeNotMatched,
)
from backend.base.definitions import (
    Constants,
    DateType,
    FilenameData,
    IssueMetadata,
    SpecialVersion,
    VolumeData,
    VolumeMetadata,
)
from backend.base.file_extraction import (
    extract_issue_number,
    extract_volume_number,
    volume_regex,
)
from backend.base.files import folder_path
from backend.base.helpers import (
    AsyncSession,
    DictKeyedDict,
    batched,
    force_range,
    normalise_string,
    to_number_cv_id,
    to_string_cv_id,
)
from backend.base.logging import LOGGER
from backend.implementations.matching import match_title, match_year
from backend.internals.db import DBConnection, get_db
from backend.internals.settings import Settings

translation_regex = compile(
    r"^<p>\s*\w+ publication(\.?</p>$|,\s| \(in the \w+ language\)|, translates )|"
    + r"^<p>\s*published by the \w+ wing of|"
    + r"^<p>\s*\w+ translations? of|"
    + r"from \w+</p>$|"
    + r"^<p>\s*published in \w+|"
    + r"^<p>\s*\w+ language|"
    + r"^<p>\s*\w+ edition of|"
    + r"^<p>\s*\w+ reprint of|"
    + r"^<p>\s*\w+ trade collection of",
    IGNORECASE,
)
headers = {"h2", "h3", "h4", "h5", "h6"}
lists = {"ul", "ol"}


def _clean_description(description: str, short: bool = False) -> str:
    """Reduce the size of the volume/issue description (written in html) to only
    essential information. Removes images, lists (e.g. of authors), and fixes
    links that have a relative URL.

    Args:
        description (str): The description to clean.
        short (bool, optional): Only remove images and fix links.
            Defaults to False.

    Returns:
        str: The cleaned description.
    """
    if not description:
        return description

    soup = BeautifulSoup(description, "html.parser")

    # Remove images
    for el in soup.find_all(["figure", "img"]):
        el.decompose()

    if not short:
        # Remove everything after the first title with list
        removed_elements = []
        for el in soup:
            if not isinstance(el, Tag):
                continue

            elif el.name is None:
                continue

            elif removed_elements or el.name in headers:
                removed_elements.append(el)

            elif el.name in lists:
                removed_elements.append(el)
                prev_sib = el.previous_sibling
                if prev_sib is not None and prev_sib.text.endswith(":"):
                    removed_elements.append(prev_sib)

            elif el.name == "p":
                children = list(getattr(el, "children", []))
                if 1 <= len(children) <= 2 and children[0].name in (
                    "b",
                    "i",
                    "strong",
                ):
                    removed_elements.append(el)

        for el in removed_elements:
            if isinstance(el, Tag):
                el.decompose()

    # Fix links
    for link in soup.select("a"):
        link.attrs = {
            k: v for k, v in link.attrs.items() if not k.startswith("data-")
        }
        link["target"] = "_blank"
        link["href"] = str(link.attrs.get("href", "")).lstrip(".").lstrip("/")
        if not str(link.attrs.get("href", "http")).startswith("http"):
            link["href"] = (
                Constants.CV_SITE_URL + "/" + str(link.attrs.get("href", ""))
            )

    result = str(soup)
    return result


class ComicVine:
    one_issue_match = (
        SpecialVersion.TPB,
        SpecialVersion.ONE_SHOT,
        SpecialVersion.HARD_COVER,
        SpecialVersion.OMNIBUS,
    )
    """
    If a volume is one of these types, it can only match to CV search results
    with one issue.
    """

    def __init__(self, comicvine_api_key: str | None = None) -> None:
        """Start interacting with ComicVine.

        Args:
            comicvine_api_key (Union[str, None], optional): Override the API key
            that is used.
                Defaults to None.

        Raises:
            InvalidComicVineApiKey: No ComicVine API key is set in the settings.
        """
        settings = Settings().get_settings()
        self.api_url = Constants.CV_API_URL
        api_key = comicvine_api_key or settings.comicvine_api_key
        if not api_key:
            raise InvalidComicVineApiKey

        self.date_type = settings.date_type.value

        # Place the cache db at the same place as the Kapowarr db
        cache_file_location = join(
            dirname(DBConnection.file) or folder_path(*Constants.DB_FOLDER),
            Constants.CV_CACHE_NAME,
        )

        self.cache = SQLiteCache(path=Path(cache_file_location))
        self.ssn = Comicvine(api_key=api_key, cache=self.cache)
        return

    def remove_from_cache(self, endpoint: str, cv_id: int) -> None:
        _cv_id = str(cv_id)
        with self.cache.connection as conn:
            cache_keys = conn.execute(
                "SELECT query FROM queries;",
            ).fetchall()

            for _key in cache_keys:
                key: str = _key["query"]
                if (
                    key.startswith(Constants.CV_API_URL + "/" + endpoint)
                    and key.count(_cv_id) != 0
                ):
                    self.cache.delete(key)

    async def __call_request(
        self, session: AsyncSession, url: str
    ) -> bytes | None:
        """Fetch a URL and get it's content async (with error handling).

        Args:
            session (AsyncSession): The aiohttp session to make the request with.
            url (str): The URL to make the request to.

        Returns:
            Union[bytes, None]: The content in bytes.
                `None` in case of error.
        """
        try:
            return await session.get_content(url)
        except ClientError:
            return None

    def __format_volume_output(
        self, volume_data: Volume | BasicVolume
    ) -> VolumeMetadata:
        """Format the ComicVine API output containing the info
        about the volume.

        Args:
            volume_data (Dict[str, Any]): The ComicVine API output.

        Returns:
            VolumeMetadata: The formatted version.
        """
        from backend.implementations.naming import generate_volume_folder_name

        title = normalise_string(volume_data.name or "")
        publisher = (
            volume_data.publisher.name if volume_data.publisher else None
        )
        description = _clean_description(volume_data.description or "")
        site_url = str(volume_data.site_url)

        result = VolumeMetadata(
            comicvine_id=volume_data.id,
            title=title,
            year=volume_data.start_year,
            volume_number=1,
            cover_link=str(volume_data.image.small_url),
            cover=None,
            description=description,
            site_url=site_url,
            aliases=[
                a.strip()
                for a in (volume_data.aliases or "").split("\r\n")
                if a
            ],
            publisher=publisher,
            issue_count=volume_data.issue_count,
            translated=False,
            already_added=None,  # Only used when searching
            issues=None,  # Only used for certain fetches
            folder_name=generate_volume_folder_name(
                VolumeData(
                    id=-1,
                    comicvine_id=volume_data.id,
                    libgen_series_id=None,
                    marvel_id=None,
                    title=title,
                    alt_title=None,
                    year=volume_data.start_year or 0,
                    publisher=publisher or "",
                    volume_number=1,
                    description=description,
                    site_url=site_url,
                    monitored=False,
                    monitor_new_issues=False,
                    root_folder=1,
                    folder="",
                    custom_folder=False,
                    special_version=SpecialVersion.NORMAL,
                    special_version_locked=False,
                    last_cv_fetch=0,
                )
            ),
        )

        if translation_regex.match(result["description"] or "") is not None:
            result["translated"] = True

        volume_result = volume_regex.search(volume_data.summary or "")
        if volume_result:
            result["volume_number"] = (
                force_range(extract_volume_number(volume_result.group(1)))[0]
                or 1
            )

        return result

    def __format_issue_output(
        self, issue_data: Issue | BasicIssue
    ) -> IssueMetadata:
        """Format the ComicVine API output containing the info
        about the issue.

        Args:
            issue_data (Dict[str, Any]): The ComicVine API output.

        Returns:
            VolumeMetadata: The formatted version.
        """
        cin = force_range(extract_issue_number(issue_data.number or "0"))[0]

        issue_date: date | None = None

        if self.date_type == DateType.COVER_DATE:
            issue_date = issue_data.cover_date
        elif self.date_type == DateType.STORE_DATE:
            issue_date = issue_data.store_date
        elif self.date_type == DateType.OLDEST_DATE:
            dates: list[date] = [
                idate
                for idate in [issue_data.cover_date, issue_data.store_date]
                if idate is not None
            ]
            if len(dates) != 0:
                issue_date = min(dates)

        result = IssueMetadata(
            comicvine_id=issue_data.id,
            volume_id=issue_data.volume.id,
            issue_number=(issue_data.number or "0").replace("/", "-").strip(),
            calculated_issue_number=cin if cin is not None else 0.0,
            title=normalise_string(issue_data.name or "") or None,
            date=issue_date,
            description=_clean_description(
                issue_data.description or "", short=True
            ),
        )
        return result

    def __format_search_output(
        self, search_results: list[BasicVolume]
    ) -> list[VolumeMetadata]:
        """Format the search results from the ComicVine API.

        Args:
            search_results (List[Dict[str, Any]]): The unformatted search
            results.

        Returns:
            List[VolumeMetadata]: The formatted search results.
        """
        cursor = get_db()

        formatted_results = [
            self.__format_volume_output(r) for r in search_results
        ]

        # Mark entries that are already added
        volume_ids: dict[int, int] = dict(
            cursor.execute(f"""
            SELECT comicvine_id, id
            FROM volumes
            WHERE {
                " OR ".join(
                    "comicvine_id = " + str(r["comicvine_id"])
                    for r in formatted_results
                )
            }
            LIMIT 50;
        """)
        )

        for r in formatted_results:
            r["already_added"] = volume_ids.get(r["comicvine_id"])

        LOGGER.debug(
            f"Searching for volumes with query result: {formatted_results}"
        )
        return formatted_results

    def test_token(self) -> bool:
        """Test if the token works.

        Returns:
            bool: Whether the token works.
        """

        async def _test_token() -> bool:
            try:
                self.ssn.get_publisher(publisher_id=31)

            except (ServiceError, AuthenticationError):
                return False

            return True

        return run(_test_token())

    async def fetch_volume(self, cv_id: str | int) -> VolumeMetadata:
        """Get the metadata of a volume from ComicVine, including its issues.

        Args:
            cv_id (Union[str, int]): The CV ID of the volume.

        Raises:
            VolumeNotMatched: No volume found with given ID in CV DB.
            CVRateLimitReached: The ComicVine rate limit is reached.

        Returns:
            VolumeMetadata: The metadata of the volume, including issues.
        """
        try:
            cv_id = to_number_cv_id((cv_id,))[0]
        except ValueError:
            raise VolumeNotMatched

        LOGGER.debug(f"Fetching volume data for {cv_id}")

        try:
            result = self.ssn.get_volume(volume_id=cv_id)

            volume_info = self.__format_volume_output(result)

            LOGGER.debug(f"Fetching issue data for volume {cv_id}")
            volume_info["issues"] = await self.fetch_issues((cv_id,))

            LOGGER.debug(f"Fetching volume data result: {volume_info}")
            async with AsyncSession() as session:
                volume_info["cover"] = await self.__call_request(
                    session, volume_info["cover_link"]
                )
            return volume_info
        except (ServiceError, AuthenticationError):
            raise CVRateLimitReached

    async def fetch_volumes(
        self, cv_ids: Sequence[str | int]
    ) -> list[VolumeMetadata]:
        """Get the metadata of the volumes from ComicVine, without their issues.

        Args:
            cv_ids (Sequence[Union[str, int]]): The CV ID's of the volumes.

        Returns:
            List[VolumeMetadata]: The metadata of the volumes, without issues.
        """
        try:
            formatted_cv_ids = to_string_cv_id(cv_ids)
        except ValueError:
            raise VolumeNotMatched

        LOGGER.debug(f"Fetching volume data for {formatted_cv_ids}")

        volume_infos = []
        async with AsyncSession() as session:
            batch_brake_time = Constants.CV_BRAKE_TIME * 10
            # 10 requests of 100 vol per round
            for request_batch in batched(formatted_cv_ids, 1000):
                if request_batch[0] != formatted_cv_ids[0]:
                    # From second round on
                    LOGGER.debug(
                        f"Waiting {Constants.CV_BRAKE_TIME}s to keep the CV rate limit happy"
                        f"Waiting {batch_brake_time}s to keep the CV rate limit happy"
                    )
                    await sleep(batch_brake_time)

                # Fetch 10 batches of 100 volumes
                try:
                    responses = [
                        self.ssn.list_volumes(
                            params={
                                "filter": f"id:{'|'.join(id_batch)}",
                            }
                        )
                        for id_batch in batched(request_batch, 100)
                    ]
                except (ServiceError, AuthenticationError):
                    raise CVRateLimitReached

                # Format volume responses and prep cover requests
                cover_map: dict[int, Any] = {}
                current_infos: list[VolumeMetadata] = []
                for batch in responses:
                    for result in batch:
                        volume_info = self.__format_volume_output(result)
                        current_infos.append(volume_info)

                        cover_map[volume_info["comicvine_id"]] = (
                            self.__call_request(
                                session, volume_info["cover_link"]
                            )
                        )

                # Fetch covers and add them to the volume info
                cover_responses = dict(
                    zip(cover_map.keys(), await gather(*cover_map.values()))
                )
                for vi in current_infos:
                    vi["cover"] = cover_responses.get(vi["comicvine_id"])

                # Add volume info of this round to total list
                volume_infos.extend(current_infos)

        return volume_infos

    async def fetch_issues(
        self, cv_ids: Sequence[str | int]
    ) -> list[IssueMetadata]:
        """Get the metadata of the issues of volumes from ComicVine.

        Args:
            ids (Sequence[Union[str, int]]): The CV ID's of the volumes.

        Returns:
            List[IssueMetadata]: The metadata of all the issues inside the
            volumes (assuming the rate limit wasn't reached).
        """
        try:
            formatted_cv_ids = to_string_cv_id(cv_ids)
        except ValueError:
            raise VolumeNotMatched

        LOGGER.debug(f"Fetching issue data for volumes {formatted_cv_ids}")

        issue_infos = []
        batch_brake_time = Constants.CV_BRAKE_TIME * 10
        for id_batch in batched(formatted_cv_ids, 50):
            try:
                results = self.ssn.list_issues(
                    params={
                        "filter": f"volume:{'|'.join(id_batch)}",
                    }
                )

            except (ServiceError, AuthenticationError):
                break

            issue_infos += [self.__format_issue_output(r) for r in results]

            if len(results) > 100:
                for offset_batch in batched(range(100, len(results), 100), 10):
                    if offset_batch[0] != 100:
                        # From second round on
                        LOGGER.debug(
                            f"Waiting {batch_brake_time}s to keep the CV rate limit happy"
                        )
                        await sleep(batch_brake_time)

                    try:
                        responses = [
                            self.ssn.list_issues(
                                params={
                                    "filter": f"volume:{'|'.join(id_batch)}",
                                    "offset": offset,
                                }
                            )
                            for offset in offset_batch
                        ]

                        for batch in responses:
                            issue_infos += [
                                self.__format_issue_output(r) for r in batch
                            ]
                    except (ServiceError, AuthenticationError):
                        raise CVRateLimitReached

        unique = []
        seen = set()

        for item in issue_infos:
            if item["comicvine_id"] not in seen:
                seen.add(item["comicvine_id"])
                unique.append(item)

        return unique

    async def search_volumes(self, query: str) -> list[VolumeMetadata]:
        """Search for volumes in CV.

        Args:
            query (str): The query to use when searching.

        Returns:
            List[VolumeMetadata]: A list with search results.
        """
        LOGGER.debug(f"Searching for volumes with the query {query}")

        try:
            if query.startswith(("4050-", "cv:")):
                try:
                    return [
                        await self.fetch_volume(to_number_cv_id((query,))[0])
                    ]

                except ValueError:
                    return []

            else:
                results: list = self.ssn.search(
                    query=query,
                    resource=ComicvineResource.VOLUME,
                    max_results=50,
                )

        except (ServiceError, AuthenticationError):
            return []

        if not results or results == [[]]:
            return []

        return self.__format_search_output(results)

    async def filenames_to_cvs(
        self, file_datas: Sequence[FilenameData], only_english: bool
    ) -> DictKeyedDict:
        """Match filenames to CV volumes.

        Args:
            file_datas (Sequence[FilenameData]): The filename data's to find CV
            volumes for.
            only_english (bool): Only match to english volumes.

        Returns:
            DictKeyedDict: A map of the filename to it's CV match.
        """
        results = DictKeyedDict()

        # If multiple filenames have the same series title, avoid searching for
        # it multiple times. Instead search for all unique titles and then later
        # match the filename back to the title's search results. This makes it
        # one search PER SERIES TITLE instead of one search PER FILENAME.
        titles_to_files: dict[str, list[FilenameData]] = {}
        for file_data in file_datas:
            (
                titles_to_files.setdefault(
                    file_data["series"].lower(), []
                ).append(file_data)
            )

        # Titles to search results
        responses = await gather(
            *(self.search_volumes(title) for title in titles_to_files)
        )

        # Filter for each title: title, only_english
        titles_to_results: dict[str, list[VolumeMetadata]] = {}
        for title, response in zip(titles_to_files, responses):
            titles_to_results[title] = [
                r
                for r in response
                if match_title(title, r["title"])
                and (only_english and not r["translated"] or not only_english)
            ]

        for title, files in titles_to_files.items():
            for file in files:
                # Filter: SV - issue_count
                filtered_results = [
                    r
                    for r in titles_to_results[title]
                    if file["special_version"] not in self.one_issue_match
                    or r["issue_count"] == 1
                ]

                if not filtered_results:
                    results[file] = {
                        "id": None,
                        "title": None,
                        "issue_count": None,
                        "link": None,
                    }
                    continue

                # Pref: exact year (1 point, also matches fuzzy year),
                #       fuzzy year (1 point),
                #       volume number (2 points)
                filtered_results.sort(
                    key=lambda r: int(r["year"] == file["year"])
                    + int(match_year(r["year"], file["year"]))
                    + int(
                        file["volume_number"] is not None
                        and r["volume_number"] == file["volume_number"]
                    )
                    * 2,
                    reverse=True,
                )

                matched_result = filtered_results[0]
                results[file] = {
                    "id": matched_result["comicvine_id"],
                    "title": f"{matched_result['title']} ({matched_result['year']})",
                    "issue_count": matched_result["issue_count"],
                    "link": matched_result["site_url"],
                }

        return results
