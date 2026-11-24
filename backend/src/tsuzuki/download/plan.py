"""Choose the downloader and worker count for this machine."""

from dataclasses import dataclass

from tsuzuki.download.aria2 import Aria2Downloader, is_available
from tsuzuki.download.base import Downloader
from tsuzuki.download.hint import aria2_install_hint
from tsuzuki.download.pipeline import FallbackDownloader, Notice, ignore_notice
from tsuzuki.download.stream import StreamDownloader


@dataclass(frozen=True)
class DownloadPlan:
    downloader: Downloader
    workers: int
    hint: str | None = None  # set when aria2c is missing, so the front-end can advise


def plan_downloads(
    requested_workers: int,
    *,
    aria2_present: bool | None = None,
    notice: Notice = ignore_notice,
    capture_progress: bool = False,
) -> DownloadPlan:
    """With aria2c: parallel workers. Without: sequential downloads plus an install hint."""
    present = is_available() if aria2_present is None else aria2_present
    if present:
        downloader = FallbackDownloader(
            Aria2Downloader(capture_progress=capture_progress), StreamDownloader(), notice
        )
        return DownloadPlan(downloader, requested_workers)
    return DownloadPlan(
        FallbackDownloader(None, StreamDownloader(), notice),
        workers=1,
        hint=aria2_install_hint(),
    )
