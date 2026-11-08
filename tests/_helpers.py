"""Small builders used by several test files."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from tsuzuki.storage import (
    EpisodeRecord,
    SeriesRecord,
    find_episode,
    lifecycle,
    list_episodes,
    sync_episodes,
    upsert_series,
)

URL = "https://animeheaven.me/anime.php?abc12"


def make_series(
    conn: sqlite3.Connection, now: datetime, *, url: str = URL, title: str = "Sample Show"
) -> SeriesRecord:
    return upsert_series(conn, site="animeheaven", url=url, title=title, now=now)


def make_episodes(
    conn: sqlite3.Connection,
    series_id: int,
    now: datetime,
    numbers: tuple[str, ...] = ("1", "2", "3"),
) -> list[EpisodeRecord]:
    """Episodes as the site lists them (newest first), returned oldest first."""
    listed = [(number, f"ref-{number}") for number in reversed(numbers)]
    sync_episodes(conn, series_id, listed, now)
    return list_episodes(conn, series_id, newest_first=False)


def make_ready(
    conn: sqlite3.Connection,
    downloads: Path,
    series_id: int,
    number: str,
    now: datetime,
    *,
    ttl: timedelta = timedelta(hours=24),
    content: bytes = b"video-bytes",
) -> tuple[EpisodeRecord, Path]:
    """Walk an episode to ``ready`` with a real file on disk."""
    episode = find_episode(conn, series_id, number)
    assert episode is not None
    lifecycle.queue(conn, episode.id, now)
    lifecycle.start(conn, episode.id, now)
    path = downloads / f"episode_{number}.mp4"
    path.write_bytes(content)
    record = lifecycle.finish(
        conn, episode.id, now, file_path=str(path), size_bytes=len(content), expires_at=now + ttl
    )
    return record, path
