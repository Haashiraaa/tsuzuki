"""Built-in downloader: chunked streaming that resumes partial files.

Used when aria2c is missing or fails. Partial files are kept on failure so the next
attempt can continue from where it stopped.
"""

from collections.abc import Iterator
from pathlib import Path

import requests

from tsuzuki.core.errors import DownloadError, FetchError
from tsuzuki.core.events import ProgressEvent, ProgressHandler
from tsuzuki.core.models import DownloadJob
from tsuzuki.download.base import Outcome
from tsuzuki.net.http import STREAM_TIMEOUT, merged_headers, to_fetch_error

CHUNK_SIZE = 1024 * 1024
RANGE_NOT_SATISFIABLE = 416
PARTIAL_CONTENT = 206


class StreamDownloader:
    def download(self, job: DownloadJob, on_progress: ProgressHandler) -> Outcome:
        job.directory.mkdir(parents=True, exist_ok=True)
        existing = existing_size(job.path)
        with open_stream(job, existing) as response:
            start = start_offset(response, existing)
            total = total_size(response, start)
            write_body(response, job, start, total, on_progress)
        verify_size(job.path, total)
        return "downloaded"


def existing_size(path: Path) -> int:
    return path.stat().st_size if path.is_file() else 0


def request_headers(job: DownloadJob, existing: int) -> dict[str, str]:
    headers = merged_headers(job.source.headers)
    if existing:
        headers["Range"] = f"bytes={existing}-"
    return headers


def open_stream(job: DownloadJob, existing: int) -> requests.Response:
    """Start the request. A rejected resume range wipes the partial so the retry starts clean."""
    response = send_request(job, existing)
    if existing and response.status_code == RANGE_NOT_SATISFIABLE:
        response.close()
        job.path.unlink(missing_ok=True)
        raise DownloadError("Server rejected the resume range; restarting from scratch")
    check_status(job, response)
    return response


def send_request(job: DownloadJob, existing: int) -> requests.Response:
    try:
        return requests.get(
            job.source.url,
            headers=request_headers(job, existing),
            stream=True,
            timeout=STREAM_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise to_fetch_error(job.source.url, exc) from exc


def check_status(job: DownloadJob, response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.RequestException as exc:
        response.close()
        raise to_fetch_error(job.source.url, exc) from exc


def start_offset(response: requests.Response, existing: int) -> int:
    """Resume only if the server answered our Range request with 206; otherwise start over."""
    return existing if existing and response.status_code == PARTIAL_CONTENT else 0


def total_size(response: requests.Response, start: int) -> int:
    """Expected final size in bytes, or 0 when the server didn't say."""
    length = int(response.headers.get("content-length") or 0)
    return start + length if length else 0


def write_body(
    response: requests.Response,
    job: DownloadJob,
    start: int,
    total: int,
    on_progress: ProgressHandler,
) -> None:
    done = start
    on_progress(ProgressEvent(job.filename, done, total))
    with open(job.path, "ab" if start else "wb") as handle:
        for chunk in iter_chunks(response, job):
            handle.write(chunk)
            done += len(chunk)
            on_progress(ProgressEvent(job.filename, done, total))


def iter_chunks(response: requests.Response, job: DownloadJob) -> Iterator[bytes]:
    """Yield body chunks, turning mid-stream network errors into retryable ``FetchError``."""
    try:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                yield chunk
    except requests.RequestException as exc:
        raise FetchError(f"{job.source.url}: {exc}", retryable=True) from exc


def verify_size(path: Path, total: int) -> None:
    """A file that doesn't match the announced size must not pass as complete."""
    size = path.stat().st_size
    if not total or size == total:
        return
    if size > total:
        path.unlink(missing_ok=True)  # over-long can't be resumed
    raise DownloadError(f"Incomplete download: expected {total} bytes, got {size}")
