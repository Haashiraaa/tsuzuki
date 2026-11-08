"""The episode life cycle: which status changes are allowed, and the function for each one.

    available -> queued -> downloading -> ready -> delivered
                    ^            |           |
                    |            v           +----> expired
                    +------- failed

``delivered``, ``expired`` and ``failed`` can be queued again, which is how an episode is
fetched a second time from the site. Every change checks the current status inside the
UPDATE itself, so two workers cannot both win the same move.
"""

import sqlite3
from datetime import datetime

from tsuzuki.core.errors import InvalidTransitionError
from tsuzuki.storage.episodes import get_episode
from tsuzuki.storage.records import EpisodeRecord, EpisodeStatus
from tsuzuki.storage.times import to_text

S = EpisodeStatus

ALLOWED: dict[EpisodeStatus, frozenset[EpisodeStatus]] = {
    S.AVAILABLE: frozenset({S.QUEUED}),
    S.QUEUED: frozenset({S.DOWNLOADING, S.AVAILABLE}),
    S.DOWNLOADING: frozenset({S.READY, S.FAILED, S.QUEUED}),
    S.READY: frozenset({S.DELIVERED, S.EXPIRED}),
    S.DELIVERED: frozenset({S.QUEUED}),
    S.EXPIRED: frozenset({S.QUEUED}),
    S.FAILED: frozenset({S.QUEUED}),
}

# The columns every change may set. Names are fixed here, never taken from outside.
CLEARED = {"file_path": None, "size_bytes": None, "expires_at": None}


def can_move(current: EpisodeStatus, target: EpisodeStatus) -> bool:
    return target in ALLOWED[current]


def move(
    conn: sqlite3.Connection,
    episode_id: int,
    target: EpisodeStatus,
    now: datetime,
    **columns: object,
) -> EpisodeRecord:
    """Change status (and optionally other columns), or raise if the move is not allowed."""
    episode = get_episode(conn, episode_id)
    if episode is None:
        raise InvalidTransitionError(f"Episode {episode_id} does not exist")
    if not can_move(episode.status, target):
        raise InvalidTransitionError(
            f"Episode {episode_id} cannot go from {episode.status.value} to {target.value}"
        )
    changed = {"status": target.value, "updated_at": to_text(now), **columns}
    assignments = ", ".join(f"{name} = ?" for name in changed)
    cursor = conn.execute(
        f"UPDATE episodes SET {assignments} WHERE id = ? AND status = ?",
        (*changed.values(), episode_id, episode.status.value),
    )
    if cursor.rowcount == 0:
        raise InvalidTransitionError(f"Episode {episode_id} changed while it was being updated")
    updated = get_episode(conn, episode_id)
    if updated is None:
        raise InvalidTransitionError(f"Episode {episode_id} disappeared while it was updated")
    return updated


def queue(conn: sqlite3.Connection, episode_id: int, now: datetime) -> EpisodeRecord:
    """Ask for an episode (again). Clears any old file info, error and attempt count."""
    return move(conn, episode_id, S.QUEUED, now, error=None, attempts=0, **CLEARED)


def cancel(conn: sqlite3.Connection, episode_id: int, now: datetime) -> EpisodeRecord:
    """Take a waiting episode back out of the queue."""
    return move(conn, episode_id, S.AVAILABLE, now)


def start(conn: sqlite3.Connection, episode_id: int, now: datetime) -> EpisodeRecord:
    previous = get_episode(conn, episode_id)
    attempts = (previous.attempts if previous else 0) + 1
    return move(conn, episode_id, S.DOWNLOADING, now, attempts=attempts)


def finish(
    conn: sqlite3.Connection,
    episode_id: int,
    now: datetime,
    *,
    file_path: str,
    size_bytes: int,
    expires_at: datetime,
) -> EpisodeRecord:
    """The file is on disk. It waits until ``expires_at`` for someone to collect it."""
    return move(
        conn,
        episode_id,
        S.READY,
        now,
        file_path=file_path,
        size_bytes=size_bytes,
        expires_at=to_text(expires_at),
        error=None,
    )


def fail(conn: sqlite3.Connection, episode_id: int, now: datetime, error: str) -> EpisodeRecord:
    return move(conn, episode_id, S.FAILED, now, error=error)


def interrupt(conn: sqlite3.Connection, episode_id: int, now: datetime) -> EpisodeRecord:
    """A download was cut off (server stopped). Back in the queue; the attempt still counts."""
    return move(conn, episode_id, S.QUEUED, now)


def deliver(conn: sqlite3.Connection, episode_id: int, now: datetime) -> EpisodeRecord:
    """The whole file reached a device. The row stays; the file is no longer on the server."""
    return move(conn, episode_id, S.DELIVERED, now, **CLEARED)


def expire(conn: sqlite3.Connection, episode_id: int, now: datetime) -> EpisodeRecord:
    """Nobody collected the file in time. The row stays; the file is no longer on the server."""
    return move(conn, episode_id, S.EXPIRED, now, **CLEARED)
