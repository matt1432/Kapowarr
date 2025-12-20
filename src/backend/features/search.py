from asyncio import gather, run

from libgencomics import LibgenException, LibgenSearch, ResultFile

from backend.base.definitions import (
    QUERY_FORMATS,
    Constants,
    MatchedSearchResultData,
    SearchResultData,
    SearchResultMatchData,
    SearchSource,
    SpecialVersion,
    VolumeData,
)
from backend.base.file_extraction import extract_filename_data
from backend.base.helpers import (
    AsyncSession,
    check_overlapping_issues,
    extract_year_from_date,
    force_range,
    get_subclasses,
)
from backend.base.logging import LOGGER
from backend.implementations.comicvine import ComicVine
from backend.implementations.getcomics import search_getcomics
from backend.implementations.matching import check_search_result_match
from backend.implementations.volumes import Volume
from backend.internals.settings import Settings


def _rank_search_result(
    result: SearchResultData,
    match_data: SearchResultMatchData,
    title: str,
    volume_number: int,
    year: tuple[int | None, int | None] = (None, None),
    calculated_issue_number: float | None = None,
) -> list[int]:
    """Give a search result a rank, based on which you can sort.

    Args:
        result (MatchedSearchResultData): A search result.

        title (str): Title of volume.

        volume_number (int): The volume number of the volume.

        year (Tuple[Union[int, None], Union[int, None]], optional): The year of
        the volume and the year of the issue if searching for an issue and
        release date is known.
            Defaults to (None, None).

        calculated_issue_number (Union[float, None], optional): The
        calculated_issue_number of the issue.
            Defaults to None.

    Returns:
        List[int]: A list of numbers which determines the ranking of the result.
    """
    rating: list[int] = []

    # Prefer matches (False == 0 == higher rank)
    rating.append(int(not match_data["match"]))

    # The more words in the search term that are present in
    # the search results' title, the higher ranked it gets
    split_title = title.split(" ")
    rating.append(
        len(
            [
                word
                for word in result["series"].split(" ")
                if word not in split_title
            ]
        )
    )

    # Prefer volume number or year matches, even better if both match
    vy_score = 3
    if (
        result["volume_number"] is not None
        and result["volume_number"] == volume_number
    ):
        vy_score -= 1

    if (
        year[1] is not None
        and result["year"] is not None
        and year[1] == result["year"]
    ):
        # issue year direct match
        vy_score -= 2

    elif (
        year[0] is not None
        and year[1] is not None
        and result["year"] is not None
        and year[0] - 1 <= result["year"] <= year[1] + 1
    ):
        # fuzzy match between start year and issue year
        vy_score -= 1

    rating.append(vy_score)

    # Sort on issue number fitting
    if calculated_issue_number is not None:
        # Search was for issue
        if (
            isinstance(result["issue_number"], float)
            and calculated_issue_number == result["issue_number"]
        ):
            # Issue number is direct match
            rating.append(0)

        elif isinstance(result["issue_number"], tuple):
            if (
                result["issue_number"][0]
                <= calculated_issue_number
                <= result["issue_number"][1]
            ):
                # Issue number falls between range
                rating.append(
                    int(
                        1
                        - (
                            1
                            / (
                                result["issue_number"][1]
                                - result["issue_number"][0]
                                + 1
                            )
                        )
                    )
                )

            else:
                # Issue number falls outside so release is not useful
                rating.append(3)

        elif result["special_version"] is not None:
            # Issue number not found but is special version
            rating.append(2)

        else:
            # No issue number found and not special version
            rating.append(3)

    else:
        # Search was for volume
        if isinstance(result["issue_number"], tuple):
            rating.append(
                int(
                    1.0
                    / (
                        result["issue_number"][1]
                        - result["issue_number"][0]
                        + 1
                    )
                )
            )

        elif isinstance(result["issue_number"], float):
            rating.append(1)

    return rating


class SearchGetComics(SearchSource):
    async def search(self, session: AsyncSession) -> list[SearchResultData]:
        if not Settings().sv.enable_getcomics:
            return []
        return await search_getcomics(session, self.query)


class SearchLibgenPlus(SearchSource):
    def get_file_result(
        self,
        libgen_file_url: str,
        volume_data: VolumeData,
    ) -> list[SearchResultData]:
        results: list[SearchResultData] = []

        file_id = int(libgen_file_url.split("file.php?id=")[-1])
        file_result = ResultFile(
            id=file_id, libgen_site_url=Constants.LIBGEN_SITE_URL
        )

        filename = file_result.filename

        if filename:
            efd = extract_filename_data(filename)

            results.append(
                SearchResultData(
                    series=volume_data.title,
                    year=volume_data.year,
                    volume_number=efd["volume_number"],
                    special_version=efd["special_version"],
                    issue_number=efd["issue_number"],
                    annual=efd["annual"],
                    is_image_file=efd["is_image_file"],
                    is_metadata_file=efd["is_metadata_file"],
                    link=f"{Constants.LIBGEN_SITE_URL}/file.php?md5={file_result.get('md5')}",
                    display_title=filename,
                    source="Libgen+",
                    filesize=file_result.filesize,
                    pages=file_result.pages or 0,
                    releaser=file_result.releaser or "",
                    scan_type=file_result.scan_type or "",
                    resolution=file_result.resolution or "",
                    dpi=file_result.dpi or "",
                    extension=file_result.extension or "",
                    comics_id=int(file_result.get("comics_id"))
                    if file_result.get("comics_id") is not None
                    else None,
                    md5=file_result.get("md5"),
                    web_sub_title=None,
                )
            )
        return results

    async def search(
        self,
        session: AsyncSession,
    ) -> list[SearchResultData]:
        results: list[SearchResultData] = []

        settings = Settings().sv

        if not settings.enable_libgen:
            return results

        volume_data = self.volume.get_data()

        libgen_series_id: str | None = None

        if volume_data.libgen_series_id is not None:
            libgen_series_id = volume_data.libgen_series_id

        series_ids = (
            list(map(int, libgen_series_id.split(",")))
            if libgen_series_id is not None and libgen_series_id != ""
            else None
        )

        issue_number = (
            int(self.issue_number)
            if isinstance(self.issue_number, float)
            and self.issue_number.is_integer()
            else self.issue_number
        )

        file_results: list[ResultFile] = []

        try:
            flaresolverr_url = (
                settings.flaresolverr_base_url + Constants.FS_API_BASE
                if settings.flaresolverr_base_url != ""
                else None
            )
            file_results = await LibgenSearch().search_comicvine_id(
                query=self.query,
                api_key=settings.comicvine_api_key,
                id=self.volume.get_data().comicvine_id,
                issue_number=issue_number,
                libgen_series_id=series_ids,
                libgen_site_url=Constants.LIBGEN_SITE_URL,
                flaresolverr_url=flaresolverr_url,
                cv_cache=ComicVine().cache,
            )
        except LibgenException as e:
            LOGGER.info(e)

        resulting_libgen_series_ids: set[str] = set()

        for file_result in file_results:
            issue = file_result.issue

            filename = file_result.filename

            if not filename:
                continue

            if not settings.include_cover_only_files:
                # we want to filter out cover only files
                if (
                    file_result.get("scan_content") or ""
                ) == "cover only" or file_result.pages == 1:
                    continue

            if not settings.include_scanned_books:
                # we want to filter out physically scanned books
                if (file_result.scan_type or "") != "digital":
                    continue

            if issue is not None:
                try:
                    if isinstance(issue.series.id, int):
                        resulting_libgen_series_ids.add(str(issue.series.id))
                except Exception:
                    pass

            efd = extract_filename_data(filename)

            results.append(
                SearchResultData(
                    series=issue.series.title or "" if issue else efd["series"],
                    year=issue.year if issue else efd["year"],
                    volume_number=efd["volume_number"],
                    special_version=efd["special_version"],
                    issue_number=efd["issue_number"],
                    annual=efd["annual"],
                    is_image_file=efd["is_image_file"],
                    is_metadata_file=efd["is_metadata_file"],
                    link=f"{Constants.LIBGEN_SITE_URL}/file.php?md5={file_result.get('md5')}",
                    display_title=filename,
                    source="Libgen+",
                    filesize=file_result.filesize,
                    pages=file_result.pages or 0,
                    releaser=file_result.releaser or "",
                    scan_type=file_result.scan_type or "",
                    resolution=file_result.resolution or "",
                    dpi=file_result.dpi or "",
                    extension=file_result.extension or "",
                    comics_id=int(file_result.get("comics_id"))
                    if file_result.get("comics_id") is not None
                    else None,
                    md5=file_result.get("md5"),
                    web_sub_title=None,
                )
            )

        if (
            not volume_data.libgen_series_id
            and len(resulting_libgen_series_ids) != 0
        ):
            self.volume.update(
                {
                    "libgen_series_id": ",".join(resulting_libgen_series_ids),
                }
            )

        return results


async def search_multiple_queries(
    *queries: str,
    volume: Volume,
    issue_number: float | None,
) -> list[SearchResultData]:
    """Do a manual search for multiple queries asynchronously.

    Returns:
        List[SearchResultData]: The search results for all queries together,
        duplicates removed.
    """
    async with AsyncSession() as session:
        searches = [
            Source(
                query=query,
                volume=volume,
                issue_number=issue_number,
            ).search(session)
            for Source in get_subclasses(SearchSource)
            for query in queries
        ]
        responses = await gather(*searches)

    search_results: list[SearchResultData] = []
    processed_links = set()
    for response in responses:
        for result in response:
            result_id = f"{result['link']}-{result['web_sub_title'] or ''}"

            # Don't add if the link is already in the results
            # Avoids duplicates, as multiple formats can return the same result
            if result_id not in processed_links:
                search_results.append(result)
                processed_links.add(result_id)

    return search_results


def manual_search(
    volume_id: int,
    issue_id: int | None = None,
    libgen_file_url: str | None = None,
) -> list[MatchedSearchResultData]:
    """Do a manual search for a volume or issue.

    Args:
        volume_id (int): The id of the volume to search for.
        issue_id (Union[int, None], optional): The id of the issue to search for,
        in the case that you want to search for an issue instead of a volume.
            Defaults to None.

    Returns:
        List[MatchedSearchResultData]: List with search results.
    """
    volume = Volume(volume_id)
    volume_data = volume.get_data()
    volume_issues = volume.get_issues()
    number_to_year: dict[float, int | None] = {
        i.calculated_issue_number: extract_year_from_date(i.date)
        for i in volume_issues
    }
    issue_number: str | None = None
    calculated_issue_number: float | None = None

    if issue_id and volume_data.special_version in (
        SpecialVersion.NORMAL,
        SpecialVersion.VOLUME_AS_ISSUE,
    ):
        issue_data = volume.get_issue(issue_id).get_data()
        issue_number = issue_data.issue_number
        calculated_issue_number = issue_data.calculated_issue_number

    LOGGER.info(
        "Starting manual search: %s (%d) %s",
        volume_data.title,
        volume_data.year,
        f"#{calculated_issue_number}" if calculated_issue_number else "",
    )

    for title in (volume_data.title, volume_data.alt_title):
        if not title:
            continue

        if volume_data.special_version == SpecialVersion.TPB:
            formats = QUERY_FORMATS["TPB"]

        elif volume_data.special_version == SpecialVersion.VOLUME_AS_ISSUE:
            formats = QUERY_FORMATS["VAI"]

        elif issue_number is None:
            formats = QUERY_FORMATS["Volume"]

        else:
            formats = QUERY_FORMATS["Issue"]

        if volume_data.year is None:
            formats = tuple(f.replace("({year})", "").strip() for f in formats)

        search_title = title.replace(":", "")
        search_titles: list[str] = [search_title]

        if search_title.startswith("The "):
            search_titles.append(search_title[4:])

        search_results: list[SearchResultData] = []

        if (
            Settings().sv.enable_libgen
            and libgen_file_url is not None
            and libgen_file_url.count("file.php?id=") != 0
        ):
            libgen_search = SearchLibgenPlus(
                query=search_title,
                volume=volume,
                issue_number=calculated_issue_number,
            )
            search_results = libgen_search.get_file_result(
                libgen_file_url=libgen_file_url,
                volume_data=volume_data,
            )

        else:
            search_results = run(
                search_multiple_queries(
                    *(
                        format.format(
                            title=stitle,
                            volume_number=volume_data.volume_number,
                            year=volume_data.year,
                            issue_number=issue_number,
                        )
                        for format in formats
                        for stitle in search_titles
                    ),
                    volume=volume,
                    issue_number=calculated_issue_number,
                )
            )

        if not search_results:
            continue

        results: list[MatchedSearchResultData] = []

        for result in search_results:
            if (
                volume_data.special_version == SpecialVersion.VOLUME_AS_ISSUE
                and result["issue_number"] is None
            ):
                result["issue_number"] = result["volume_number"]

            match_data = check_search_result_match(
                result,
                volume_data,
                volume_issues,
                number_to_year,
                calculated_issue_number,
            )
            results.append(
                {
                    **result,
                    **match_data,
                    "rank": _rank_search_result(
                        result,
                        match_data,
                        search_title,
                        volume_data.volume_number,
                        (
                            volume_data.year,
                            number_to_year.get(calculated_issue_number or 0),
                        ),
                        calculated_issue_number,
                    ),
                }
            )

        # Sort results; put best result at top
        results.sort(key=lambda r: r["rank"] if "rank" in r else [])

        LOGGER.debug("Manual search results: %s", results)
        return results

    return []


def auto_search(
    volume_id: int, issue_id: int | None = None
) -> list[MatchedSearchResultData]:
    """Search for a volume or issue and automatically choose a result.

    Args:
        volume_id (int): The ID of the volume to search for.
        issue_id (Union[int, None], optional): The id of the issue to search for,
        in the case that you want to search for an issue instead of a volume.
            Defaults to None.

    Returns:
        List[MatchedSearchResultData]: List with chosen search results.
    """
    volume = Volume(volume_id)
    volume_data = volume.get_data()
    special_version = volume_data.special_version
    LOGGER.info(
        "Starting auto search for volume %d %s",
        volume_id,
        f"issue {issue_id}" if issue_id else "",
    )

    searchable_issues: list[tuple[int, float]] = []
    if not volume_data.monitored:
        # Volume is unmonitored so don't auto search
        pass

    elif issue_id is None:
        # Auto search volume
        # Get open issues (monitored and no file).
        searchable_issues = volume.get_open_issues()

    else:
        # Auto search issue
        issue = volume.get_issue(issue_id)
        issue_data = issue.get_data()
        if issue_data.monitored and not issue.get_files():
            # Issue is open
            searchable_issues = [(issue_id, issue_data.calculated_issue_number)]

    if not searchable_issues:
        # No issues to search for
        issue_result: list[MatchedSearchResultData] = []
        LOGGER.debug(f"Auto search results: {issue_result}")
        return issue_result

    search_results = [
        r for r in manual_search(volume_id, issue_id) if r["match"]
    ]

    if issue_id is not None or (
        special_version.value is not None
        and special_version != SpecialVersion.VOLUME_AS_ISSUE
    ):
        # We're searching for one "item", so just grab first search result.
        issue_result = search_results[:1] if search_results else []
        LOGGER.debug("Auto search results: %s", issue_result)
        return issue_result

    # We're searching for a volume, so we might download multiple search results.
    # Find a combination of search results that download the most issues.
    chosen_downloads: list[MatchedSearchResultData] = []
    searchable_issue_numbers = {i[1] for i in searchable_issues}
    for result in search_results:
        if not Settings().sv.auto_search_torrents:
            result["comics_id"] = None

        # Determine what issues the result covers
        if result["issue_number"] is not None:
            # Normal issue, VAS with issue number,
            # OS/HC/Omnibus using issue 1
            result["_issue_number"] = result["issue_number"]
            covered_issues = volume.get_issues_in_range(
                *force_range(result["issue_number"])
            )

        elif (
            special_version == SpecialVersion.VOLUME_AS_ISSUE
            and result["special_version"] == SpecialVersion.TPB
        ):
            # VAS with volume number
            if result["volume_number"] is None:
                continue

            if isinstance(result["volume_number"], tuple):
                result["_issue_number"] = (
                    float(result["volume_number"][0]),
                    float(result["volume_number"][1]),
                )
            else:
                result["_issue_number"] = float(result["volume_number"])

            covered_issues = volume.get_issues_in_range(
                *force_range(result["volume_number"])
            )

        elif special_version in (
            SpecialVersion.ONE_SHOT,
            SpecialVersion.HARD_COVER,
            SpecialVersion.TPB,
            SpecialVersion.OMNIBUS,
        ) and result["special_version"] in (
            special_version,
            SpecialVersion.TPB,
        ):
            # OS/HC/Omnibus using no issue number, TPB
            result["_issue_number"] = 1.0
            covered_issues = volume.get_issues()

        else:
            continue

        if any(
            i.calculated_issue_number not in searchable_issue_numbers
            for i in covered_issues
        ):
            # Part or all of what the result covers is already downloaded
            continue

        # Check that any other selected download doesn't already cover the issue
        for part in chosen_downloads:
            if check_overlapping_issues(
                part.get("_issue_number", 0.0), result["_issue_number"]
            ):
                break
        else:
            chosen_downloads.append(result)

    # Find issues that have still not been covered. Might've been that the
    # download for the issue simply did not pop up on volume search, but will
    # when searching for the individual issue.
    missing_issues = [
        i
        for i in searchable_issues
        if not any(
            check_overlapping_issues(i[1], part.get("_issue_number", 0.0))
            for part in chosen_downloads
        )
    ]

    for missing_issue in missing_issues:
        chosen_downloads.extend(auto_search(volume_id, missing_issue[0]))

    LOGGER.debug("Auto search results: %s", chosen_downloads)
    return chosen_downloads
