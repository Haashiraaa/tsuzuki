"""HTTP helpers: default headers, timeouts, and translating errors into ``FetchError``."""

from collections.abc import Mapping

import requests

from tsuzuki.core.errors import FetchError

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
# (connect, read) seconds. Every request must have one: requests waits forever otherwise.
PAGE_TIMEOUT = (10.0, 30.0)
STREAM_TIMEOUT = (10.0, 60.0)


def merged_headers(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    """Default headers with ``extra`` layered on top."""
    return {"User-Agent": DEFAULT_USER_AGENT, **(extra or {})}


def fetch_text(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    cookies: Mapping[str, str] | None = None,
    timeout: tuple[float, float] = PAGE_TIMEOUT,
) -> str:
    """GET a page and return its body. Raises ``FetchError`` on any failure."""
    try:
        response = requests.get(
            url,
            headers=merged_headers(headers),
            cookies=dict(cookies) if cookies else None,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise to_fetch_error(url, exc) from exc
    return response.text


def to_fetch_error(url: str, exc: requests.RequestException) -> FetchError:
    return FetchError(f"{url}: {exc}", retryable=is_transient(exc))


def is_transient(exc: requests.RequestException) -> bool:
    """Timeouts, dropped connections, 429 and 5xx may heal; 404 and bad URLs won't."""
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else 0
        return status == 429 or status >= 500
    return isinstance(exc, requests.Timeout | requests.ConnectionError)
