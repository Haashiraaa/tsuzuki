"""How long a finished file may stay on the server, and how much of it we will hold."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from tsuzuki.storage.episodes import ready_bytes

DEFAULT_TTL = timedelta(hours=24)


@dataclass(frozen=True)
class RetentionPolicy:
    """``ttl``: a finished file is removed this long after it is ready if nobody collected it.
    ``max_ready_bytes``: stop starting downloads when waiting files reach this size (None = no cap).
    """

    ttl: timedelta = DEFAULT_TTL
    max_ready_bytes: int | None = None


def expiry_for(now: datetime, policy: RetentionPolicy) -> datetime:
    return now + policy.ttl


def has_room(conn: sqlite3.Connection, policy: RetentionPolicy, incoming_bytes: int = 0) -> bool:
    """False when adding ``incoming_bytes`` would push waiting files past the cap."""
    if policy.max_ready_bytes is None:
        return True
    return ready_bytes(conn) + incoming_bytes <= policy.max_ready_bytes
