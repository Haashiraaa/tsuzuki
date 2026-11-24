"""What a download worker needs from the database: take the next queued episode, and tidy up
after a crash or a cancel."""

import sqlite3
from datetime import datetime

from tsuzuki.core.errors import InvalidTransitionError
from tsuzuki.storage import lifecycle
from tsuzuki.storage.database import transaction
from tsuzuki.storage.episodes import list_by_status
from tsuzuki.storage.records import EpisodeRecord, EpisodeStatus
from tsuzuki.storage.retention import RetentionPolicy, has_room

# Which queued episode goes next. Each queued episode belongs to the visitor who asked first.
# A visitor's turn comes up by (episodes of theirs already downloading) + (their place in their
# own queue), so with free slots everyone's first episode goes before anyone's second, and a
# visitor who queued 200 cannot starve a visitor who queued 1. Ties go to the earlier request.
FAIR_NEXT_SQL = """
WITH owner AS (
    SELECT episode_id, visitor_id, MIN(requested_at) AS asked_at
    FROM requests WHERE delivered_at IS NULL GROUP BY episode_id
),
running AS (
    SELECT o.visitor_id, COUNT(*) AS n
    FROM episodes e JOIN owner o ON o.episode_id = e.id
    WHERE e.status = 'downloading' GROUP BY o.visitor_id
),
waiting AS (
    SELECT e.id, o.visitor_id, COALESCE(o.asked_at, e.updated_at) AS asked_at,
           ROW_NUMBER() OVER (
               PARTITION BY o.visitor_id ORDER BY COALESCE(o.asked_at, e.updated_at), e.id
           ) - 1 AS place
    FROM episodes e LEFT JOIN owner o ON o.episode_id = e.id
    WHERE e.status = 'queued'
)
SELECT w.id FROM waiting w LEFT JOIN running r ON r.visitor_id = w.visitor_id
ORDER BY w.place + COALESCE(r.n, 0), w.asked_at, w.id LIMIT 1
"""


def claim_next(
    conn: sqlite3.Connection, now: datetime, policy: RetentionPolicy
) -> EpisodeRecord | None:
    """Take the longest-waiting queued episode and mark it downloading, or return None.

    Nothing is taken while finished files already fill the disk allowance (``policy``), so a
    full disk pauses the queue instead of failing downloads. Two workers can never take the
    same episode: the move to ``downloading`` only succeeds for one of them.
    """
    if not has_room(conn, policy):
        return None
    row = conn.execute(FAIR_NEXT_SQL).fetchone()
    if row is None:
        return None
    try:
        with transaction(conn):
            return lifecycle.start(conn, row["id"], now)
    except InvalidTransitionError:
        return None  # another worker got there first; the next poll finds the next one


def recover_interrupted(conn: sqlite3.Connection, now: datetime) -> int:
    """Episodes still marked downloading when the server starts were cut off by a crash or a
    restart. Put them back in the queue (partial files are resumed). Returns how many."""
    stuck = list_by_status(conn, [EpisodeStatus.DOWNLOADING])
    for record in stuck:
        with transaction(conn):
            lifecycle.interrupt(conn, record.id, now)
    return len(stuck)


def abandon(conn: sqlite3.Connection, episode_id: int, now: datetime) -> EpisodeRecord:
    """A running download was cancelled: back to the library as not requested."""
    with transaction(conn):
        lifecycle.interrupt(conn, episode_id, now)
        return lifecycle.cancel(conn, episode_id, now)
