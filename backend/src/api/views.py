"""Turn storage records into the shapes the frontend shows."""

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
from tsuzuki.core.progress import ProgressBoard
from tsuzuki.storage import (
    EpisodeRecord,
    EpisodeStatus,
    RequestRecord,
    SeriesSummary,
    open_rows,
    view_status,
)

S = EpisodeStatus
STARTING = "Starting"
EXAMPLE_FILE = "Downloads/Series-name/episode_1.mp4"
WAITING_NOTE = "Waiting for a free slot"
EXPIRED_NOTE = "Expired: it was not saved in time. Queue it again."


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


def episode_view(record: EpisodeRecord, request: RequestRecord | None) -> EpisodeOut:
    """One episode as this visitor sees it: the file is shared, "delivered" is personal."""
    return EpisodeOut(
        id=record.id, number=record.number, status=view_status(record.status, request).value
    )


def display_name(title: str, number: str) -> str:
    return f"{title} · Episode {number}"


def failure_note(record: EpisodeRecord) -> str:
    reason = (record.error or "unknown error").rstrip(".")
    return f"Failed: {reason}. Safe to retry."


def queue_view(
    conn: sqlite3.Connection,
    board: ProgressBoard,
    visitor_id: int | None,
    *,
    downloads: Path,
    slots: int,
) -> QueueOut:
    """The queue screen for one visitor: only the episodes they asked for."""
    rows = [] if visitor_id is None else open_rows(conn, visitor_id)
    active: list[ActiveOut] = []
    waiting: list[WaitingOut] = []
    finished: list[FinishedOut] = []
    ready: list[EpisodeRecord] = []
    for row in rows:
        episode = row.episode
        name = display_name(row.series_title, episode.number)
        if episode.status is S.DOWNLOADING:
            active.append(active_view(episode, name, board))
        elif episode.status is S.QUEUED:
            waiting.append(WaitingOut(id=episode.id, name=name, note=WAITING_NOTE, failed=False))
        elif episode.status is S.FAILED:
            waiting.append(
                WaitingOut(id=episode.id, name=name, note=failure_note(episode), failed=True)
            )
        elif episode.status is S.EXPIRED:
            waiting.append(WaitingOut(id=episode.id, name=name, note=EXPIRED_NOTE, failed=True))
        elif episode.status is S.READY:
            finished.append(FinishedOut(id=episode.id, name=name))
            ready.append(episode)
    return QueueOut(
        active=active,
        waiting=waiting,
        finished=finished,
        slots=slots,
        downloads_folder=downloads.name,
        example_file=example_file(ready, downloads),
    )


def active_view(record: EpisodeRecord, name: str, board: ProgressBoard) -> ActiveOut:
    progress = board.get(record.id)
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
