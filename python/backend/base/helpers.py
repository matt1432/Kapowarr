"""
General "helper" functions and classes
"""

from __future__ import annotations

from asyncio import sleep
from base64 import urlsafe_b64encode
from collections import deque
from collections.abc import (
    Callable,
    Collection,
    Generator,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from hashlib import pbkdf2_hmac
from multiprocessing.pool import AsyncResult, MapResult, Pool
from os import cpu_count, sep
from os.path import basename, dirname
from sys import version_info
from typing import (
    TYPE_CHECKING,
    Any,
)
from urllib.parse import unquote

from aiohttp import ClientError, ClientResponse, ClientSession
from backend.base.definitions import Constants
from backend.base.logging import LOGGER, get_log_filepath
from bencoding import bdecode
from multidict import CIMultiDict, CIMultiDictProxy
from requests import Session as RSession
from requests.adapters import HTTPAdapter, Retry
from requests.structures import CaseInsensitiveDict
from yarl import URL

if TYPE_CHECKING:
    from multiprocessing.pool import IMapIterator

    from flask.ctx import AppContext


def get_python_version() -> str:
    """Get python version as string

    Returns:
        str: The python version
    """
    return ".".join(str(i) for i in list(version_info))


def check_python_version() -> bool:
    """Check if the python version that is used is a minimum version.

    Returns:
        bool: Whether or not the python version is version 3.12 or above or not.
    """
    if not (version_info.major == 3 and version_info.minor >= 12):
        LOGGER.critical(
            "The minimum python version required is python3.12 "
            "(currently "
            + str(version_info.major)
            + "."
            + str(version_info.minor)
            + "."
            + str(version_info.micro)  # noqa
            + ")."
        )  # noqa
        return False
    return True


def get_subclasses(
    *classes: type[Any],
    include_self: bool = False,
    recursive: bool = True,
    only_leafs: bool = False,
) -> list[type[Any]]:
    """Get subclasses of the given classes.

    Args:
        *classes (type): The classes to get subclasses from.
        include_self (bool, optional): Whether or not to include the classes
            themselves. Defaults to False.
        recursive (bool, optional): Whether or not to get all subclasses
            recursively. Defaults to True.
        only_leafs (bool, optional): Whether or not to only return leaf classes.
            Defaults to False.

    Returns:
        List[type]: The subclasses.
    """
    result: list[type[Any]] = []
    if include_self:
        result.extend(classes)

    if not recursive:
        result.extend(
            subclass for current in classes for subclass in current.__subclasses__()
        )
        return result

    to_do = deque(classes)
    while to_do:
        current = to_do.popleft()
        subclasses = current.__subclasses__()
        if subclasses:
            to_do.extend(subclasses)
            if not only_leafs and current not in classes:
                result.append(current)
        else:
            result.append(current)

    return result


def batched[T](l_val: Sequence[T], n: int) -> Generator[Sequence[T], Any, Any]:
    """Iterate over l_val in batches.

    Args:
        l_val (Sequence[T]): The list to iterate over.
        n (int): The batch size.

    Yields:
        Generator[Sequence[T], Any, Any]: A batch of size n from l_val
    """
    for ndx in range(0, len(l_val), n):
        yield l_val[ndx : ndx + n]


def reversed_tuples[T, U](i: Iterable[tuple[T, U]]) -> Generator[tuple[U, T], Any, Any]:
    """Yield sub-tuples in reversed order.

    Args:
        i (Iterable[Tuple[T, U]]): Iterator.

    Yields:
        Generator[Tuple[U, T], Any, Any]: Sub-tuple with reversed order.
    """
    for entry_1, entry_2 in i:
        yield entry_2, entry_1


def get_first_of_range[T](n: T | tuple[T, ...] | list[T]) -> T:
    """Get the first element from a variable that could potentially be a range,
    but could also be a single value. In the case of a single value, the value
    is returned.

    Args:
        n (Union[T, Tuple[T, ...], List[T]]): The range or single value.

    Returns:
        T: The first element or single value.
    """
    if isinstance(n, tuple | list):
        return n[0]
    else:
        return n


def create_range[T](n: T | tuple[T, ...] | list[T]) -> Sequence[T]:
    """Create range if input isn't already.

    Args:
        n (Union[T, Tuple[T, ...], List[T]]): The value or range.

    Returns:
        Sequence[T]: The range.
    """
    if isinstance(n, tuple | list):
        return n
    else:
        return (n, n)


def force_suffix(source: str, suffix: str = sep) -> str:
    """Add `suffix` to `source`, but only if it's not already there.

    Args:
        source (str): The string to process.
        suffix (str, optional): The suffix to apply. Defaults to sep.

    Returns:
        str: The resulting string with suffix applied.
    """
    if source.endswith(suffix):
        return source
    else:
        return source + suffix


def check_filter[T](element: T, collection: Collection[T]) -> bool:
    """Check if `element` is in `collection`, but only if `collection` has
    content, otherwise return True. Useful as filtering where an empty filter
    is possible.

    Args:
        element (T): The element to check for.
        collection (Collection[T]): The collection. If empty, True is returned.

    Returns:
        bool: Whether the element is in the collection if the collection has
        content, otherwise True.
    """
    return True if not collection else (element in collection)


def filtered_iter[T](
    elements: Iterable[T], collection: Collection[T]
) -> Generator[T, Any, Any]:
    """Yields elements from `elements` but an element is only yielded if
    `collection` is empty or if the element is in `collection`. Useful as
    applying the filter `collection` to elements where an empty filter is
    possible.

    Args:
        elements (Iterable[T]): The elements to iterate over and yield.
        collection (Collection[T]): The collection. If empty, all elements of
        `elements` are returned.

    Yields:
        Generator[T, Any, Any]: All elements in `elements` if `collection` is
        empty, otherwise only elements that are in `collection`.
    """
    for el in elements:
        if check_filter(el, collection):
            yield el
    return


def normalize_string(s: str) -> str:
    """Fix some common stuff in strings coming from online sources. Parses
    html escapes (`%20` -> ` `), fixing encoding errors (`_28` -> `(`),
    removing surrounding whitespace and replaces unicode chars by standard
    chars (`’` -> `'`).

    Args:
        s (str): Input string.

    Returns:
        str: Normalized string.
    """
    return (
        unquote(s)
        .replace("_28", "(")
        .replace("_29", ")")
        .replace("–", "-")
        .replace("’", "'")
        .strip()
    )


def normalize_number(s: str) -> str:
    """Turn user-entered numbers (in string form) into more handable versions.
    Handles locale, unknown numbers, trailing chars, surrounding whitespace,
    etc.

    Args:
        s (str): Input string representing a(n) (issue) number.

    Returns:
        str: Normalized string.
    """
    return s.replace(",", ".").replace("?", "0").rstrip(".").strip().lower()


def normalize_year(s: str) -> int | None:
    """Turn user-entered years (in string form) into an int if possible.
    Handles unknown numbers, trailing chars, surrounding whitespace,
    etc.

    Args:
        s (str): Input string representing a year.

    Returns:
        str: Normalized string.
    """
    if not s:
        return None

    s = (
        s.strip()
        .replace("-", "0")
        .replace(",", "/")
        .replace("?", "")
        .replace(">", "")
        .replace("<", "")
        .replace("+", "")
        .replace(".", "")
    )

    if "/" in s:
        s = next((e for e in s.split("/") if len(e) == 4), "")

    if s and s.isdigit():
        return int(s)
    return None


def normalize_base_url(base_url: str) -> str:
    """Turn user-entered base URL's into a standard format. No trailing slash,
    and `http://` prefix applied if no protocol is found.

    Args:
        base_url (str): Input base URL.

    Returns:
        str: Normalized base URL.
    """
    result = base_url.rstrip("/")
    if not result.startswith(("http://", "https://")):
        result = f"http://{result}"
    return result


def extract_year_from_date[T](
    date: str | None, default: T | None = None
) -> int | T | None:
    """Get the year from a date in the format YYYY-MM-DD

    Args:
        date (Union[str, None]): The date.
        default (T, optional): Value if year can't be extracted.
            Defaults to None.

    Returns:
        Union[int, T]: The year or the default value.
    """
    if date:
        try:
            return int(date.split("-")[0])
        except ValueError:
            return default
    else:
        return default


def to_number_cv_id(ids: Iterable[str | int]) -> list[int]:
    """Convert CV ID's into numbers.

    Args:
        ids (Iterable[Union[str, int]]): CV ID's. Can have any common format,
        like 123, "123", "4050-123", "cv:123" and "cv:4050-123".

    Raises:
        ValueError: Invalid CV ID.

    Returns:
        List[int]: The converted CV ID's, in format `NNNN`
    """
    result: list[int] = []
    for i in ids:
        if isinstance(i, int):
            result.append(i)
            continue

        if i.startswith("cv:"):
            i = i.partition(":")[2]

        if i.isdigit():
            result.append(int(i))

        elif i.startswith("4050-") and i.replace("-", "").isdigit():
            result.append(int(i.split("4050-")[-1]))

        else:
            raise ValueError

    return result


def to_string_cv_id(ids: Iterable[str | int]) -> list[str]:
    """Convert CV ID's into short strings.

    Args:
        ids (Iterable[Union[str, int]]): CV ID's. Same formats supported as
        `to_number_cv_id()`.

    Raises:
        ValueError: Invalid CV ID.

    Returns:
        List[str]: The converted CV ID's, in format `"NNNN"`.
    """
    return [str(i) for i in to_number_cv_id(ids)]


def to_full_string_cv_id(ids: Iterable[str | int]) -> list[str]:
    """Convert CV ID's into long strings.

    Args:
        ids (Iterable[Union[str, int]]): CV ID's. Same formats supported as
        `to_number_cv_id()`.

    Raises:
        ValueError: Invalid CV ID.

    Returns:
        List[str]: The converted CV ID's, in format `"4050-NNNN"`.
    """
    return ["4050-" + str(i) for i in to_number_cv_id(ids)]


def check_overlapping_issues(
    issues_1: float | tuple[float, float],
    issues_2: float | tuple[float, float],
) -> bool:
    """Check if two issues overlap. Both can be single issues or ranges.

    Args:
        issues_1 (Union[float, Tuple[float, float]]): First issue or range.
        issues_2 (Union[float, Tuple[float, float]]): Second issue or range.

    Returns:
        bool: Whether or not they overlap.
    """
    if isinstance(issues_1, float | int):
        if isinstance(issues_2, float | int):
            return issues_1 == issues_2
        else:
            return issues_2[0] <= issues_1 <= issues_2[1]
    else:
        if isinstance(issues_2, float | int):
            return issues_1[0] <= issues_2 <= issues_1[1]
        else:
            return (
                issues_1[0] <= issues_2[0] <= issues_1[1]
                or issues_1[0] <= issues_2[1] <= issues_1[1]
            )


def first_of_column[T](columns: Iterable[Sequence[T]]) -> list[T]:
    """Get the first element of each sub-array.

    Args:
        columns (Iterable[Sequence[T]]): List of sub-arrays.

    Returns:
        List[T]: List with first value of each sub-array.
    """
    return [e[0] for e in columns]


def fix_year(year: int) -> int:
    """Fix year numbers that are probably a typo.
    E.g. 2204 -> 2024, 1890 -> 1980, 2010 -> 2010

    Args:
        year (int): The possibly broken year.

    Returns:
        int: The fixed year or input year if not broken.
    """
    if 1900 <= year < 2100:
        return year

    year_str = list(str(year))
    if len(year_str) != 4:
        return year

    return int(year_str[0] + year_str[2] + year_str[1] + year_str[3])


def hash_password(salt: bytes, password: str) -> str:
    """Hash a password.

    Args:
        salt (bytes): The salt to use with the hash.
        password (str): The password the hash.

    Returns:
        str: The resulting hash.
    """
    return urlsafe_b64encode(
        pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    ).decode()


def get_torrent_info(torrent: bytes) -> dict[bytes, Any]:
    """Get the info from the contents of a torrent file.

    Args:
        torrent (bytes): The contents of a torrent file.

    Returns:
        Dict[bytes, Any]: The info.
    """
    return bdecode(torrent)[b"info"]  # type: ignore


class Singleton(type):
    _instances: dict[str, type] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> type:
        c = str(cls)
        if c not in cls._instances:
            cls._instances[c] = super().__call__(*args, **kwargs)

        return cls._instances[c]


class CommaList(list):
    """
    Normal list but init can also take a string with comma seperated values:
        `'blue,green,red'` -> `['blue', 'green', 'red']`.
    Using str() will convert it back to a string with comma seperated values.
    """

    def __init__(self, value: str | Iterable):
        if not isinstance(value, str):
            super().__init__(value)
            return

        if not value:
            super().__init__([])
        else:
            super().__init__(value.split(","))
        return

    def __str__(self) -> str:
        return ",".join(self)


class DictKeyedDict(dict):
    """
    Normal dict but key is dict.
    """

    def __convert_dict(self, key: Mapping) -> str:
        converted_key = ",".join(sorted(key.keys()) + sorted(map(str, key.values())))
        return converted_key

    def __getitem__(self, key: Mapping) -> Any:
        return super().__getitem__(self.__convert_dict(key))[1]

    def get(self, key: Mapping, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key: Mapping, value: Any) -> None:
        return super().__setitem__(self.__convert_dict(key), (key, value))

    def setdefault(self, key: Mapping, default: Any = None) -> Any:
        if key not in self:
            self[key] = default

        return self[key]

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, Mapping):
            return False

        return super().__contains__(self.__convert_dict(key))

    def keys(self) -> Iterator[Any]:  # type: ignore
        return (v[0] for v in super().values())

    def values(self) -> Iterator[Any]:  # type: ignore
        return (v[1] for v in super().values())

    def items(self) -> Iterator[tuple[Any, Any]]:  # type: ignore
        return zip(self.keys(), self.values())


class Session(RSession):
    """
    Inherits from `requests.Session`. Adds retries, sets user agent and handles
    CloudFlare blockages using FlareSolverr.
    """

    def __init__(self) -> None:
        from backend.implementations.flaresolverr import FlareSolverr

        super().__init__()

        self.fs = FlareSolverr()

        retries = Retry(
            total=Constants.TOTAL_RETRIES,
            backoff_factor=Constants.BACKOFF_FACTOR_RETRIES,  # type: ignore
            status_forcelist=Constants.STATUS_FORCELIST_RETRIES,
        )
        self.mount("http://", HTTPAdapter(max_retries=retries))
        self.mount("https://", HTTPAdapter(max_retries=retries))

        self.headers.update({"User-Agent": Constants.DEFAULT_USERAGENT})

        return

    def request(  # type: ignore
        self,
        method,
        url: str,
        params=None,
        data=None,
        headers: dict[str, str] | None = None,
        cookies=None,
        files=None,
        auth=None,
        timeout=None,
        allow_redirects=True,
        proxies=None,
        hooks=None,
        stream=None,
        verify=None,
        cert=None,
        json=None,
    ):
        ua, cf_cookies = self.fs.get_ua_cookies(url)
        self.headers.update({"User-Agent": ua})
        self.cookies.update(cf_cookies)

        for round in range(1, 3):
            result = super().request(
                method,
                url,
                params,
                data,
                headers,
                cookies,
                files,
                auth,
                timeout,
                allow_redirects,
                proxies,
                hooks,
                stream,
                verify,
                cert,
                json,
            )

            if round == 1 and result.status_code == 403:
                fs_result = self.fs.handle_cf_block(url, result.headers)

                if not fs_result:
                    # FlareSolverr couldn't solve the problem or it wasn't
                    # needed
                    continue

                result.url = fs_result["url"]
                result.status_code = fs_result["status"]
                result._content = fs_result["response"].encode("utf-8")
                result.headers = CaseInsensitiveDict(fs_result["headers"])

            if 400 <= result.status_code < 500:
                LOGGER.warning(
                    f"{result.request.method} request to {result.request.url} returned with code {result.status_code}"
                )
                LOGGER.debug(
                    f"Request response for {result.request.method} {result.request.url}: %s",
                    result.text,
                )

            return result


class AsyncSession(ClientSession):
    """
    Inherits from `aiohttp.ClientSession`. Adds retries, sets user agent and
    handles CloudFlare blockages using FlareSolverr.
    """

    def __init__(self) -> None:
        from backend.implementations.flaresolverr import FlareSolverr

        super().__init__(headers={"User-Agent": Constants.DEFAULT_USERAGENT})

        self.fs = FlareSolverr()

        return

    async def _request(self, *args: Any, **kwargs: Any) -> ClientResponse:
        sleep_time = Constants.BACKOFF_FACTOR_RETRIES

        ua, cf_cookies = self.fs.get_ua_cookies(args[1])
        self.headers.update({"User-Agent": ua})
        self.cookie_jar.update_cookies(cf_cookies)

        for round in range(1, Constants.TOTAL_RETRIES + 1):
            try:
                response = await super()._request(*args, **kwargs)

                if response.status in Constants.STATUS_FORCELIST_RETRIES:
                    raise ClientError

            except ClientError as e:
                if round == Constants.TOTAL_RETRIES:
                    raise e

                LOGGER.warning(
                    f"{args[0]} request failed for url {args[1]}. "
                    f"Retrying for round {round + 1}..."
                )

                await sleep(sleep_time)
                sleep_time *= 2
                continue

            if round == 1 and response.status == 403:
                fs_result = await self.fs.handle_cf_block_async(
                    self, args[1], response.headers
                )

                if not fs_result:
                    # FlareSolverr couldn't solve the problem or it wasn't
                    # needed
                    continue

                response._url = URL(fs_result["url"])
                response.status = fs_result["status"]
                response._body = fs_result["response"].encode("utf-8")
                response._headers = CIMultiDictProxy(CIMultiDict(fs_result["headers"]))

            if response.status >= 400:
                LOGGER.warning(
                    f"{args[0]} request to {args[1]} returned with code {response.status}"
                )
                LOGGER.debug(
                    f"Request response for {args[0]} {args[1]}: %s",
                    await response.text(),
                )

            return response

        raise ClientError

    async def __aenter__(self) -> AsyncSession:
        return self

    async def get_text(
        self, url: str, params: dict[str, Any] = {}, headers: dict[str, Any] = {}
    ) -> str:
        """Fetch a page and return the body.

        Args:
            url (str): The URL to fetch from.
            params (Dict[str, Any], optional): Any additional params.
                Defaults to {}.
            headers (Dict[str, Any], optional): Any additional headers.
                Defaults to {}.

        Returns:
            str: The body of the response.
        """
        async with self.get(url, params=params, headers=headers) as response:
            return await response.text()

    async def get_content(
        self, url: str, params: dict[str, Any] = {}, headers: dict[str, Any] = {}
    ) -> bytes:
        """Fetch a page and return the content in bytes.

        Args:
            url (str): The URL to fetch from.
            params (Dict[str, Any], optional): Any additional params.
                Defaults to {}.
            headers (Dict[str, Any], optional): Any additional headers.
                Defaults to {}.

        Returns:
            bytes: The content of the response.
        """
        async with self.get(url, params=params, headers=headers) as response:
            return await response.content.read()


class _ContextKeeper(metaclass=Singleton):
    _ctx: Callable[[], AppContext]

    def ctx(self):
        return self._ctx()

    def __init__(
        self,
        log_level: int | None = None,
        log_folder: str | None = None,
        log_file: str | None = None,
        db_folder: str | None = None,
    ) -> None:
        if not log_level:
            return

        from backend.internals.server import setup_process

        self.ctx = setup_process(log_level, log_folder, log_file, db_folder)
        return


def pool_apply_func(args: Any = (), kwds: Any = {}) -> Any:
    func, value = args
    with _ContextKeeper().ctx():
        return func(*value, **kwds)


def pool_map_func[T, U](func_value: tuple[Callable[[T], U], T]) -> U:
    func, value = func_value
    with _ContextKeeper().ctx():
        return func(value)


def pool_starmap_func[T, U](func: Callable[[T], U], *args: T) -> U:
    with _ContextKeeper().ctx():
        return func(*args)


class PortablePool(Pool):
    def __init__(self, max_processes: int | None = None) -> None:
        """Create a multiprocessing pool that can run on all OS'es and has
        access to the app context.

        Args:
            max_processes (Union[int, None], optional): The amount of processes
            that the pool should manage. Given int is limited to CPU count.
            Give `None` for default which is CPU count. Defaults to None.
        """
        from backend.internals.db import DBConnection

        log_file = get_log_filepath()
        super().__init__(
            processes=(
                min(cpu_count() or 1, max_processes)
                if max_processes is not None
                else None
            ),
            initializer=_ContextKeeper,
            initargs=(
                LOGGER.root.level,
                dirname(log_file),
                basename(log_file),
                dirname(DBConnection.file),
            ),
        )
        return

    def apply[U](
        self,
        func: Callable[..., U],
        args: Iterable[Any] = (),
        kwds: Mapping[str, Any] = {},
    ) -> U:
        new_args = (func, args)
        new_func = pool_apply_func
        return super().apply(new_func, new_args, kwds)

    def apply_async[T](
        self,
        func: Callable[..., T],
        args: Iterable[Any] = (),
        kwds: Mapping[str, Any] = {},
        callback: Callable[[T], object] | None = None,
        error_callback: Callable[[BaseException], object] | None = None,
    ) -> AsyncResult[T]:
        new_args = (func, args)
        new_func = pool_apply_func
        return super().apply_async(new_func, new_args, kwds, callback, error_callback)

    def map[T, U](
        self,
        func: Callable[[T], U],
        iterable: Iterable[T],
        chunksize: int | None = None,
    ) -> list[U]:
        new_iterable = ((func, i) for i in iterable)
        new_func = pool_map_func
        return super().map(new_func, new_iterable, chunksize)

    def imap[T, U](
        self,
        func: Callable[[T], U],
        iterable: Iterable[T],
        chunksize: int | None = 1,
    ) -> IMapIterator[U]:
        new_iterable = ((func, i) for i in iterable)
        new_func = pool_map_func
        return super().imap(new_func, new_iterable, chunksize)

    def imap_unordered[T, U](
        self,
        func: Callable[[T], U],
        iterable: Iterable[T],
        chunksize: int | None = 1,
    ) -> IMapIterator[U]:
        new_iterable = ((func, i) for i in iterable)
        new_func = pool_map_func
        return super().imap_unordered(new_func, new_iterable, chunksize)

    def map_async[T, U](
        self,
        func: Callable[[U], T],
        iterable: Iterable[U],
        chunksize: int | None = None,
        callback: Callable[[list[T]], object] | None = None,
        error_callback: Callable[[BaseException], object] | None = None,
    ) -> MapResult[T]:
        new_iterable = ((func, i) for i in iterable)
        new_func = pool_map_func
        return super().map_async(
            new_func, new_iterable, chunksize, callback, error_callback
        )

    def starmap[T, U](
        self,
        func: Callable[..., U],
        iterable: Iterable[Iterable[T]],
        chunksize: int | None = None,
    ) -> list[U]:
        new_iterable = ((func, *i) for i in iterable)
        new_func = pool_starmap_func
        return super().starmap(new_func, new_iterable, chunksize)

    def istarmap_unordered[T, U](
        self,
        func: Callable[..., U],
        iterable: Iterable[Iterable[T]],
        chunksize: int | None = 1,
    ) -> IMapIterator[U]:
        "A combination of starmap and imap_unordered."
        new_iterable = ((func, i) for i in iterable)
        new_func = pool_apply_func
        return super().imap_unordered(new_func, new_iterable, chunksize)

    def starmap_async[T](
        self,
        func: Callable[..., T],
        iterable: Iterable[Iterable[Any]],
        chunksize: int | None = None,
        callback: Callable[[list[T]], object] | None = None,
        error_callback: Callable[[BaseException], object] | None = None,
    ) -> AsyncResult[list[T]]:
        new_iterable = ((func, *i) for i in iterable)
        new_func = pool_starmap_func
        return super().starmap_async(
            new_func, new_iterable, chunksize, callback, error_callback
        )
