"""Fakes for the worker tests: a downloader that writes a small file, and the services that
use it, so no test touches the network or runs a real download tool."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest

from tsuzuki.core.events import ProgressHandler
from tsuzuki.core.models import DownloadJob, Episode, MediaSource, Series
from tsuzuki.core.progress import ProgressBoard
from tsuzuki.core.retry import RetryPolicy
from tsuzuki.download.base import Outcome
from tsuzuki.download.pipeline import Notice
from tsuzuki.download.plan import DownloadPlan
from tsuzuki.sites.base import Site
from tsuzuki.worker import Services, WorkerSettings

NO_WAIT = RetryPolicy(attempts=2, base_delay=0.0, max_delay=0.0)
ONCE = RetryPolicy(attempts=1)


class FakeSite:
    name = "fakesite"

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def fetch_series(self, url: str) -> Series:
        raise NotImplementedError

    def resolve_media(self, series: Series, episode: Episode) -> MediaSource:
        if self.error:
            raise self.error
        return MediaSource("https://example.test/video.mp4")


@dataclass
class FakeDownloader:
    """Writes ``size`` bytes in ``chunks`` steps, reporting progress after each one.

    ``errors`` are raised one per call before it succeeds. ``on_chunk`` lets a test act in the
    middle of a download (cancel it, look at the progress board, and so on)."""

    size: int = 1000
    chunks: int = 4
    errors: list[Exception] = field(default_factory=list[Exception])
    on_chunk: Callable[[int], None] | None = None
    calls: int = 0

    def download(self, job: DownloadJob, on_progress: ProgressHandler) -> Outcome:
        from tsuzuki.core.events import ProgressEvent

        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        job.directory.mkdir(parents=True, exist_ok=True)
        step = self.size // self.chunks
        with job.path.open("wb") as handle:
            for index in range(1, self.chunks + 1):
                handle.write(b"x" * step)
                handle.flush()
                if self.on_chunk:
                    self.on_chunk(index)
                on_progress(ProgressEvent(job.filename, step * index, self.size))
        return "downloaded"


@pytest.fixture
def board() -> ProgressBoard:
    return ProgressBoard()


@pytest.fixture
def fake_downloader() -> FakeDownloader:
    return FakeDownloader()


def make_services(
    downloader: FakeDownloader,
    board: ProgressBoard,
    now: datetime,
    *,
    site: Site | None = None,
    hint: str | None = None,
    on_plan: Callable[[Notice], None] | None = None,
) -> Services:
    chosen = site or FakeSite()

    def make_plan(notice: Notice) -> DownloadPlan:
        if on_plan:
            on_plan(notice)
        return DownloadPlan(downloader, 1, hint=hint)

    return Services(
        resolve_site=lambda _url: chosen, clock=lambda: now, board=board, make_plan=make_plan
    )


def make_settings(
    tmp_path: Path, downloads: Path, *, retry: RetryPolicy = ONCE, slots: int = 1
) -> WorkerSettings:
    return WorkerSettings(
        database=tmp_path / "test.db",
        downloads=downloads,
        slots=slots,
        retry=retry,
        poll_seconds=0.02,
    )


def queued_episode(conn: sqlite3.Connection, series_id: int, number: str, now: datetime) -> int:
    from tsuzuki.storage import find_episode, lifecycle

    episode = find_episode(conn, series_id, number)
    assert episode is not None
    lifecycle.queue(conn, episode.id, now)
    return episode.id
