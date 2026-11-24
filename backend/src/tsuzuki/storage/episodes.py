"""Episodes: record what the site lists, and read them back."""

import sqlite3
from collections.abc import Iterable, Sequence
from datetime import datetime

from tsuzuki.storage.records import EpisodeRecord, EpisodeStatus
from tsuzuki.storage.rows import episode_from_row
from tsuzuki.storage.times import to_text


def ordinal_for(number: str, position: int) -> float:
    """Sort key for an episode: its number when numeric, else its place on the page."""
    try:
        return float(number)
    except ValueError:
        return float(position)


def sync_episodes(
    conn: sqlite3.Connection, series_id: int, listed: Sequence[tuple[str, str]], now: datetime
) -> int:
    """Record the ``(number, ref)`` pairs a site lists. New ones start as available; known ones
    keep their status and only get a fresh ref. Returns how many were new."""
    before = count_episodes(conn, series_id)
    stamp = to_text(now)
    rows = [
        (series_id, number, ordinal_for(number, position), ref, stamp)
        for position, (number, ref) in enumerate(listed)
    ]
    conn.executemany(
        "INSERT INTO episodes (series_id, number, ordinal, ref, updated_at) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(series_id, number) DO UPDATE SET ref = excluded.ref",
        rows,
    )
    return count_episodes(conn, series_id) - before


def count_episodes(conn: sqlite3.Connection, series_id: int) -> int:
    row = conn.execute("SELECT COUNT(*) FROM episodes WHERE series_id = ?", (series_id,)).fetchone()
    return int(row[0])


def get_episode(conn: sqlite3.Connection, episode_id: int) -> EpisodeRecord | None:
    row = conn.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()
    return episode_from_row(row) if row else None


def find_episode(conn: sqlite3.Connection, series_id: int, number: str) -> EpisodeRecord | None:
    row = conn.execute(
        "SELECT * FROM episodes WHERE series_id = ? AND number = ?", (series_id, number)
    ).fetchone()
    return episode_from_row(row) if row else None


def list_episodes(
    conn: sqlite3.Connection, series_id: int, *, newest_first: bool = True, limit: int | None = None
) -> list[EpisodeRecord]:
    direction = "DESC" if newest_first else "ASC"
    sql = f"SELECT * FROM episodes WHERE series_id = ? ORDER BY ordinal {direction}"
    params: tuple[int, ...] = (series_id,)
    if limit is not None:
        sql += " LIMIT ?"
        params = (series_id, limit)
    return [episode_from_row(row) for row in conn.execute(sql, params).fetchall()]


def list_by_status(
    conn: sqlite3.Connection, statuses: Iterable[EpisodeStatus]
) -> list[EpisodeRecord]:
    """Episodes in any of the given statuses, oldest update first (queue order)."""
    values = [status.value for status in statuses]
    marks = ", ".join("?" for _ in values)
    rows = conn.execute(
        f"SELECT * FROM episodes WHERE status IN ({marks}) ORDER BY updated_at, id", values
    ).fetchall()
    return [episode_from_row(row) for row in rows]


def due_for_expiry(conn: sqlite3.Connection, now: datetime) -> list[EpisodeRecord]:
    """Ready episodes nobody collected before their ``expires_at``."""
    rows = conn.execute(
        "SELECT * FROM episodes WHERE status = 'ready' AND expires_at <= ? ORDER BY expires_at",
        (to_text(now),),
    ).fetchall()
    return [episode_from_row(row) for row in rows]


def ready_bytes(conn: sqlite3.Connection) -> int:
    """Disk currently held by files waiting to be collected."""
    row = conn.execute(
        "SELECT COALESCE(SUM(size_bytes), 0) FROM episodes WHERE status = 'ready'"
    ).fetchone()
    return int(row[0])


def count_by_status(conn: sqlite3.Connection) -> dict[EpisodeStatus, int]:
    rows = conn.execute("SELECT status, COUNT(*) AS n FROM episodes GROUP BY status").fetchall()
    return {EpisodeStatus(row["status"]): row["n"] for row in rows}
