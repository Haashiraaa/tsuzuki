"""The contract every downloader fulfils."""

from typing import Literal, Protocol

from backend.src.core.events import ProgressHandler
from backend.src.core.models import DownloadJob

Outcome = Literal["downloaded", "skipped"]


class Downloader(Protocol):
    def download(self, job: DownloadJob, on_progress: ProgressHandler) -> Outcome:
        """Fetch ``job`` to disk. Raises ``DownloadError`` or ``FetchError`` on failure."""
        ...
