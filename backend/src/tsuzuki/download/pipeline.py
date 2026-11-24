"""Combine downloaders: skip finished files, prefer aria2c, fall back to the built-in one."""

from collections.abc import Callable

from tsuzuki.core.errors import DownloadError
from tsuzuki.core.events import ProgressHandler
from tsuzuki.core.models import DownloadJob
from tsuzuki.download.base import Downloader, Outcome
from tsuzuki.download.existing import is_complete

Notice = Callable[[str], None]


def ignore_notice(_message: str) -> None:
    """Default notice handler: drop it."""


class FallbackDownloader:
    """``primary`` (optional) first; if it raises ``DownloadError``, use ``fallback``."""

    def __init__(
        self,
        primary: Downloader | None,
        fallback: Downloader,
        notice: Notice = ignore_notice,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._notice = notice

    def download(self, job: DownloadJob, on_progress: ProgressHandler) -> Outcome:
        if is_complete(job):
            return "skipped"
        outcome = self._try_primary(job, on_progress)
        return outcome or self._fallback.download(job, on_progress)

    def _try_primary(self, job: DownloadJob, on_progress: ProgressHandler) -> Outcome | None:
        if self._primary is None:
            return None
        try:
            return self._primary.download(job, on_progress)
        except DownloadError as exc:
            self._notice(f"{exc}. Falling back to the built-in downloader.")
            return None
