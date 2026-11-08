"""Turn storage records into the shapes the frontend shows. No database or web code here
except where a view has to look up a name, so most of it is easy to test."""

import sqlite3
from pathlib import Path

from tsuzuki.api.schemas import (
    ActiveOut,
    EpisodeOut,
    FinishedOut,
    QueueOut,
    SeriesOut,
    WaitingOut,
)
from tsuzuki.core.errors import StorageError
from tsuzuki.core.progress import ProgressBoard
from tsuzuki.storage import (
    EpisodeRecord,
    EpisodeStatus,
    SeriesSummary,
    get_series,
    list_by_status,
)

S = EpisodeStatus
STARTING = "Starting"
EXAMPLE_FILE = "Downloads/Series-name/episode_1.mp4"


def series_view(summary: SeriesSummary) -> SeriesOut:
    return SeriesOut(
        id=summary.series.id,
        title=summary.series.title,
        site=summary.series.site,
        url=summary.series.url,
        total=summary.total,
        downloaded=summary.downloaded,
        in_progress=summary.in_progress,
        failed=summary.failed,
    )


def episode_view(record: EpisodeRecord) -> EpisodeOut:
    return EpisodeOut(id=record.id, number=record.number, status=record.status.value)


def display_name(title: str, number: str) -> str:
    return f"{title} · Episode {number}"


def failure_note(record: EpisodeRecord) -> str:
    reason = (record.error or "unknown error").rstrip(".")
    return f"Failed: {reason}. Safe to retry."


def queue_view(
    conn: sqlite3.Connection,
    board: ProgressBoard,
    *,
    downloads: Path,
    slots: int,
) -> QueueOut:
    titles = TitleCache(conn)
    downloading = list_by_status(conn, [S.DOWNLOADING])
    queued = list_by_status(conn, [S.QUEUED])
    failed = list_by_status(conn, [S.FAILED])
    ready = list_by_status(conn, [S.READY])
    return QueueOut(
        active=[active_view(record, titles, board) for record in downloading],
        waiting=[
            *(waiting_view(record, titles) for record in queued),
            *(failed_view(record, titles) for record in failed),
        ],
        finished=[
            FinishedOut(id=r.id, name=display_name(titles.of(r.series_id), r.number)) for r in ready
        ],
        slots=slots,
        downloads_folder=str(downloads),
        example_file=example_file(ready, downloads),
    )


class TitleCache:
    """Series titles by id, each looked up once per view."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._titles: dict[int, str] = {}

    def of(self, series_id: int) -> str:
        if series_id not in self._titles:
            series = get_series(self._conn, series_id)
            if series is None:
                raise StorageError(f"Episode points at a missing series: {series_id}")
            self._titles[series_id] = series.title
        return self._titles[series_id]


def active_view(record: EpisodeRecord, titles: TitleCache, board: ProgressBoard) -> ActiveOut:
    progress = board.get(record.id)
    name = display_name(titles.of(record.series_id), record.number)
    if progress is None:
        return ActiveOut(
            id=record.id,
            name=name,
            method=STARTING,
            percent=0,
            bytes_done=0,
            bytes_total=0,
            bytes_per_second=0,
            eta_seconds=None,
        )
    return ActiveOut(
        id=record.id,
        name=name,
        method=progress.method or STARTING,
        percent=progress.percent,
        bytes_done=progress.bytes_done,
        bytes_total=progress.bytes_total,
        bytes_per_second=int(progress.bytes_per_second),
        eta_seconds=progress.eta_seconds,
    )


def waiting_view(record: EpisodeRecord, titles: TitleCache) -> WaitingOut:
    name = display_name(titles.of(record.series_id), record.number)
    return WaitingOut(id=record.id, name=name, note="Waiting for a free slot", failed=False)


def failed_view(record: EpisodeRecord, titles: TitleCache) -> WaitingOut:
    name = display_name(titles.of(record.series_id), record.number)
    return WaitingOut(id=record.id, name=name, note=failure_note(record), failed=True)


def example_file(ready: list[EpisodeRecord], downloads: Path) -> str:
    """Where one finished file sits, relative to the folder that holds Downloads."""
    for record in ready:
        if record.file_path:
            try:
                relative = Path(record.file_path).resolve().relative_to(downloads.resolve())
            except ValueError:
                continue
            return f"{downloads.name}/{relative.as_posix()}"
    return EXAMPLE_FILE
