import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from tests._helpers import make_episodes, make_ready, make_series
from tsuzuki.storage import (
    EpisodeStatus,
    RetentionPolicy,
    abandon,
    claim_next,
    find_episode,
    get_episode,
    lifecycle,
    recover_interrupted,
)

NO_CAP = RetentionPolicy()


def queue(conn: sqlite3.Connection, series_id: int, number: str, when: datetime) -> int:
    episode = find_episode(conn, series_id, number)
    assert episode is not None
    lifecycle.queue(conn, episode.id, when)
    return episode.id


def test_nothing_queued_means_nothing_claimed(conn: sqlite3.Connection, now: datetime) -> None:
    assert claim_next(conn, now, NO_CAP) is None


def test_the_longest_waiting_episode_is_claimed_first(
    conn: sqlite3.Connection, now: datetime
) -> None:
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    second = queue(conn, series.id, "2", now)
    first = queue(conn, series.id, "1", now + timedelta(seconds=5))
    claimed = claim_next(conn, now + timedelta(seconds=10), NO_CAP)
    assert claimed is not None
    assert claimed.id == second
    assert claimed.status is EpisodeStatus.DOWNLOADING
    assert claimed.attempts == 1
    other = claim_next(conn, now + timedelta(seconds=11), NO_CAP)
    assert other is not None
    assert other.id == first


def test_an_episode_is_never_claimed_twice(conn: sqlite3.Connection, now: datetime) -> None:
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    queue(conn, series.id, "1", now)
    assert claim_next(conn, now, NO_CAP) is not None
    assert claim_next(conn, now, NO_CAP) is None


def test_a_full_disk_allowance_pauses_the_queue(
    conn: sqlite3.Connection, downloads: Path, now: datetime
) -> None:
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    make_ready(conn, downloads, series.id, "1", now, content=b"x" * 100)
    queue(conn, series.id, "2", now)
    assert claim_next(conn, now, RetentionPolicy(max_ready_bytes=100)) is not None
    queue(conn, series.id, "3", now)
    assert claim_next(conn, now, RetentionPolicy(max_ready_bytes=50)) is None


def test_downloads_cut_off_by_a_crash_go_back_in_the_queue(
    conn: sqlite3.Connection, now: datetime
) -> None:
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    episode_id = queue(conn, series.id, "1", now)
    lifecycle.start(conn, episode_id, now)
    assert recover_interrupted(conn, now) == 1
    record = get_episode(conn, episode_id)
    assert record is not None
    assert record.status is EpisodeStatus.QUEUED
    assert recover_interrupted(conn, now) == 0


def test_abandoning_a_download_returns_it_to_the_library(
    conn: sqlite3.Connection, now: datetime
) -> None:
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    episode_id = queue(conn, series.id, "1", now)
    lifecycle.start(conn, episode_id, now)
    assert abandon(conn, episode_id, now).status is EpisodeStatus.AVAILABLE
