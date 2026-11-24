"""The contract every downloader fulfils."""

from typing import Literal, Protocol

from tsuzuki.core.events import ProgressHandler
from tsuzuki.core.models import DownloadJob

Outcome = Literal["downloaded", "skipped"]


class Downloader(Protocol):
    def download(self, job: DownloadJob, on_progress: ProgressHandler) -> Outcome:
        """Fetch ``job`` to disk. Raises ``DownloadError`` or ``FetchError`` on failure."""
        ...
