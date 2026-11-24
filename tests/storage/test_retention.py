import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from tests._helpers import make_episodes, make_ready, make_series
from tsuzuki.storage import RetentionPolicy, expiry_for, has_room


def test_default_ttl_is_a_day(now: datetime) -> None:
    assert expiry_for(now, RetentionPolicy()) == now + timedelta(hours=24)


def test_custom_ttl(now: datetime) -> None:
    assert expiry_for(now, RetentionPolicy(ttl=timedelta(hours=2))) == now + timedelta(hours=2)


def test_no_cap_always_has_room(conn: sqlite3.Connection) -> None:
    assert has_room(conn, RetentionPolicy(), incoming_bytes=10**12)


def test_cap_counts_waiting_files_plus_the_incoming_one(
    conn: sqlite3.Connection, downloads: Path, now: datetime
) -> None:
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    make_ready(conn, downloads, series.id, "1", now, content=b"x" * 60)
    policy = RetentionPolicy(max_ready_bytes=100)
    assert has_room(conn, policy, incoming_bytes=40)
    assert not has_room(conn, policy, incoming_bytes=41)
