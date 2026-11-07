"""Decide whether a file on disk is already a complete copy of the remote one."""

import requests

from tsuzuki.core.models import DownloadJob
from tsuzuki.net.http import merged_headers

HEAD_TIMEOUT = 10.0


def is_complete(job: DownloadJob) -> bool:
    """True only when the local size equals the size the server reports.

    Presence alone proves nothing (that once marked broken files as done), and if the
    server won't say how big the file is, we don't guess.
    """
    if not job.path.is_file():
        return False
    expected = remote_size(job)
    return expected is not None and expected == job.path.stat().st_size


def remote_size(job: DownloadJob) -> int | None:
    try:
        response = requests.head(
            job.source.url,
            headers=merged_headers(job.source.headers),
            allow_redirects=True,
            timeout=HEAD_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None
    return parse_length(response.headers.get("content-length"))


def parse_length(raw: str | None) -> int | None:
    """A positive integer content-length, or None."""
    if raw is None or not raw.isdigit():
        return None
    return int(raw) or None
