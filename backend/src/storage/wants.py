"""What visitors have asked for.

The download and the file are shared: if two visitors want the same episode it is fetched once.
A *request* is one visitor's claim on an episode. The server keeps the file until every visitor
who asked for it has saved it (or it expires), and deletes it after the last one.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from tsuzuki.core.errors import StorageError
from tsuzuki.storage import lifecycle
from tsuzuki.storage.episodes import get_episode
from tsuzuki.storage.records import (
    OPEN_VIEW,
    REQUESTABLE_VIEW,
    EpisodeRecord,
    EpisodeStatus,
    RequestRecord,
    view_status,
)
from tsuzuki.storage.retention import RetentionPolicy, expiry_for
from tsuzuki.storage.rows import episode_from_row
from tsuzuki.storage.times import from_text, to_text

S = EpisodeStatus


def request_from_row(row: sqlite3.Row) -> RequestRecord:
    delivered = row["delivered_at"]
    return RequestRecord(
        id=row["id"],
        visitor_id=row["visitor_id"],
        episode_id=row["episode_id"],
        requested_at=from_text(row["requested_at"]),
        delivered_at=from_text(delivered) if delivered else None,
    )


def get_request(conn: sqlite3.Connection, visitor_id: int, episode_id: int) -> RequestRecord | None:
    row = conn.execute(
        "SELECT * FROM requests WHERE visitor_id = ? AND episode_id = ?", (visitor_id, episode_id)
    ).fetchone()
    return request_from_row(row) if row else None


def requests_for_series(
    conn: sqlite3.Connection, visitor_id: int, series_id: int
) -> dict[int, RequestRecord]:
    """This visitor's requests in one series, by episode id."""
    rows = conn.execute(
        "SELECT r.* FROM requests r JOIN episodes e ON e.id = r.episode_id "
        "WHERE r.visitor_id = ? AND e.series_id = ?",
        (visitor_id, series_id),
    ).fetchall()
    return {row["episode_id"]: request_from_row(row) for row in rows}


def status_for(conn: sqlite3.Connection, visitor_id: int, episode: EpisodeRecord) -> EpisodeStatus:
    return view_status(episode.status, get_request(conn, visitor_id, episode.id))


def open_count(conn: sqlite3.Connection, visitor_id: int) -> int:
    """Episodes this visitor has waiting: queued, downloading, or ready but not yet saved."""
    marks = ", ".join("?" for _ in OPEN_VIEW)
    row = conn.execute(
        "SELECT COUNT(*) FROM requests r JOIN episodes e ON e.id = r.episode_id "
        f"WHERE r.visitor_id = ? AND r.delivered_at IS NULL AND e.status IN ({marks})",
        (visitor_id, *(s.value for s in OPEN_VIEW)),
    ).fetchone()
    return int(row[0])


def request_episode(
    conn: sqlite3.Connection,
    visitor_id: int,
    episode_id: int,
    now: datetime,
    policy: RetentionPolicy,
) -> bool:
    """Ask for an episode. Returns False if this visitor already has it open (nothing to do).

    Run inside a transaction. If nobody has the file yet it joins the queue; if it is already
    queued, downloading or ready it simply shares that, and a ready file's deadline is pushed
    back so it does not vanish just as the new visitor arrives.
    """
    episode = get_episode(conn, episode_id)
    if episode is None:
        raise StorageError(f"Episode {episode_id} does not exist")
    mine = get_request(conn, visitor_id, episode_id)
    if view_status(episode.status, mine) not in REQUESTABLE_VIEW:
        return False
    stamp = to_text(now)
    conn.execute(
        "INSERT INTO requests (visitor_id, episode_id, requested_at, delivered_at) "
        "VALUES (?, ?, ?, NULL) "
        "ON CONFLICT(visitor_id, episode_id) DO UPDATE SET "
        "requested_at = excluded.requested_at, delivered_at = NULL",
        (visitor_id, episode_id, stamp),
    )
    if episode.status in (S.AVAILABLE, S.FAILED, S.DELIVERED, S.EXPIRED):
        lifecycle.queue(conn, episode_id, now)
    elif episode.status is S.READY:
        conn.execute(
            "UPDATE episodes SET expires_at = ? WHERE id = ?",
            (to_text(expiry_for(now, policy)), episode_id),
        )
    return True


def cancel_request(
    conn: sqlite3.Connection, visitor_id: int, episode_id: int, now: datetime
) -> bool:
    """Withdraw this visitor's request. Returns True if the running download should be stopped
    (it was downloading and nobody else wants it). A queued episode nobody else wants goes back
    to the library; one somebody else wants stays queued for them."""
    conn.execute(
        "DELETE FROM requests WHERE visitor_id = ? AND episode_id = ? AND delivered_at IS NULL",
        (visitor_id, episode_id),
    )
    if undelivered_count(conn, episode_id) > 0:
        return False
    episode = get_episode(conn, episode_id)
    if episode is None:
        return False
    if episode.status is S.QUEUED:
        lifecycle.cancel(conn, episode_id, now)
    return episode.status is S.DOWNLOADING


def undelivered_count(conn: sqlite3.Connection, episode_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM requests WHERE episode_id = ? AND delivered_at IS NULL",
        (episode_id,),
    ).fetchone()
    return int(row[0])


def mark_delivered(
    conn: sqlite3.Connection, visitor_id: int, episode_id: int, now: datetime
) -> int:
    """This visitor saved the episode. Returns how many visitors still have to save it."""
    conn.execute(
        "UPDATE requests SET delivered_at = ? "
        "WHERE visitor_id = ? AND episode_id = ? AND delivered_at IS NULL",
        (to_text(now), visitor_id, episode_id),
    )
    return undelivered_count(conn, episode_id)


@dataclass(frozen=True)
class QueueRow:
    """One line of a visitor's queue: their request, the shared episode, and the series title."""

    request: RequestRecord
    episode: EpisodeRecord
    series_title: str


def open_rows(conn: sqlite3.Connection, visitor_id: int) -> list[QueueRow]:
    """Everything this visitor has asked for and not yet saved, oldest request first."""
    rows = conn.execute(
        "SELECT r.id AS r_id, r.visitor_id, r.episode_id, r.requested_at, r.delivered_at, "
        "       e.*, s.title AS series_title "
        "FROM requests r JOIN episodes e ON e.id = r.episode_id "
        "JOIN series s ON s.id = e.series_id "
        "WHERE r.visitor_id = ? AND r.delivered_at IS NULL "
        "ORDER BY r.requested_at, r.id",
        (visitor_id,),
    ).fetchall()
    result: list[QueueRow] = []
    for row in rows:
        request = RequestRecord(
            id=row["r_id"],
            visitor_id=row["visitor_id"],
            episode_id=row["episode_id"],
            requested_at=from_text(row["requested_at"]),
            delivered_at=None,
        )
        result.append(QueueRow(request, episode_from_row(row), row["series_title"]))
    return result
