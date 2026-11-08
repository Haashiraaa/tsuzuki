"""Download one episode and record how it went."""

import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from pathlib import Path

from tsuzuki.core.errors import DownloadCancelled, DownloadInterrupted, TsuzukiError
from tsuzuki.core.events import ProgressEvent
from tsuzuki.core.models import DownloadJob, Episode, Series
from tsuzuki.core.naming import episode_filename, folder_name
from tsuzuki.core.progress import ProgressBoard
from tsuzuki.core.retry import RetryPolicy, retry_call
from tsuzuki.download.pipeline import Notice
from tsuzuki.download.plan import DownloadPlan, plan_downloads
from tsuzuki.sites.base import Site
from tsuzuki.storage import (
    EpisodeRecord,
    RetentionPolicy,
    abandon,
    expiry_for,
    get_series,
    lifecycle,
    transaction,
)
from tsuzuki.storage.files import remove_file

log = logging.getLogger("tsuzuki.worker")

PlanFactory = Callable[[Notice], DownloadPlan]
BUILT_IN = "Built-in downloader"
ARIA2 = "aria2 · 8 connections"


def default_plan(notice: Notice) -> DownloadPlan:
    """One download at a time per worker slot; aria2 progress is read so the queue can show it."""
    return plan_downloads(1, notice=notice, capture_progress=True)


@dataclass(frozen=True)
class WorkerSettings:
    database: Path
    downloads: Path
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)
    slots: int = 3
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    poll_seconds: float = 2.0


@dataclass(frozen=True)
class Services:
    """The outside things a job uses. Tests replace them with fakes."""

    resolve_site: Callable[[str], Site]
    clock: Callable[[], datetime]
    board: ProgressBoard
    make_plan: PlanFactory = default_plan


def run_episode(
    conn: sqlite3.Connection,
    record: EpisodeRecord,
    settings: WorkerSettings,
    services: Services,
    should_stop: Callable[[], bool] = lambda: False,
) -> None:
    """Download one claimed episode. Never raises: every outcome is written to the database
    (ready, failed, back in the queue, or cancelled) so one bad episode cannot stop the worker."""
    board = services.board
    try:
        path = download(conn, record, settings, services, should_stop)
        finish(conn, record, path, settings, services)
    except DownloadCancelled:
        abandon(conn, record.id, services.clock())
        discard_partial(settings, record, conn)
    except DownloadInterrupted:
        with transaction(conn):
            lifecycle.interrupt(conn, record.id, services.clock())
    except (TsuzukiError, OSError) as exc:
        record_failure(conn, record, str(exc) or type(exc).__name__, services)
    except Exception as exc:  # a bug: say so on the screen, log the traceback, keep going
        log.exception("Unexpected error downloading episode %s", record.id)
        record_failure(conn, record, f"Unexpected error: {exc}", services)
    finally:
        board.clear(record.id)


def download(
    conn: sqlite3.Connection,
    record: EpisodeRecord,
    settings: WorkerSettings,
    services: Services,
    should_stop: Callable[[], bool],
) -> Path:
    series_record = get_series(conn, record.series_id)
    if series_record is None:
        raise TsuzukiError(f"Series {record.series_id} no longer exists")
    board = services.board
    check_stop(record.id, board, should_stop)

    site = services.resolve_site(series_record.url)
    series = Series(series_record.title, series_record.url, ())
    episode = Episode(record.number, record.ref)
    source = retry_call(lambda: site.resolve_media(series, episode), settings.retry)
    job = DownloadJob(
        source,
        settings.downloads / folder_name(series_record.title),
        episode_filename(record.number),
    )

    plan = services.make_plan(partial(use_built_in, board, record.id))
    board.update(record.id, done=0, total=0, method=BUILT_IN if plan.hint else ARIA2)

    def on_progress(event: ProgressEvent) -> None:
        check_stop(record.id, board, should_stop)
        board.update(record.id, done=event.done, total=event.total)

    retry_call(lambda: plan.downloader.download(job, on_progress), settings.retry)
    return job.path


def use_built_in(board: ProgressBoard, episode_id: int, _message: str) -> None:
    """aria2c failed and the built-in downloader took over: say so on the queue screen."""
    board.update(episode_id, done=0, total=0, method=BUILT_IN)


def check_stop(episode_id: int, board: ProgressBoard, should_stop: Callable[[], bool]) -> None:
    if board.cancel_requested(episode_id):
        raise DownloadCancelled(f"Episode {episode_id} was cancelled")
    if should_stop():
        raise DownloadInterrupted("The server is stopping")


def finish(
    conn: sqlite3.Connection,
    record: EpisodeRecord,
    path: Path,
    settings: WorkerSettings,
    services: Services,
) -> None:
    now = services.clock()
    with transaction(conn):
        lifecycle.finish(
            conn,
            record.id,
            now,
            file_path=str(path),
            size_bytes=path.stat().st_size,
            expires_at=expiry_for(now, settings.retention),
        )


def record_failure(
    conn: sqlite3.Connection, record: EpisodeRecord, message: str, services: Services
) -> None:
    with transaction(conn):
        lifecycle.fail(conn, record.id, services.clock(), message)


def discard_partial(
    settings: WorkerSettings, record: EpisodeRecord, conn: sqlite3.Connection
) -> None:
    """Someone cancelled on purpose, so the half-downloaded file is just taking up space."""
    series = get_series(conn, record.series_id)
    if series is None:
        return
    path = settings.downloads / folder_name(series.title) / episode_filename(record.number)
    for leftover in (path, path.with_name(path.name + ".aria2")):
        try:
            remove_file(settings.downloads, str(leftover))
        except OSError:
            log.warning("Could not remove %s", leftover)
