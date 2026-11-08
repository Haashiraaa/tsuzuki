import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from tests._helpers import make_episodes, make_library, make_ready, make_series, make_visitor
from tsuzuki.storage import (
    EpisodeRecord,
    EpisodeStatus,
    RetentionPolicy,
    abandon,
    add_to_library,
    claim_next,
    find_episode,
    get_episode,
    lifecycle,
    recover_interrupted,
    request_episode,
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


class TestFairness:
    """With free slots everyone's first episode goes before anyone's second."""

    def setup_two(
        self, conn: sqlite3.Connection, now: datetime
    ) -> tuple[int, int, list[EpisodeRecord]]:
        big, _ = make_visitor(conn, now)
        small, _ = make_visitor(conn, now)
        series, episodes = make_library(conn, big, now, numbers=tuple(str(n) for n in range(1, 7)))
        add_to_library(conn, small, series.id, now)
        return big, small, episodes

    def test_a_small_request_is_not_stuck_behind_a_big_one(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        big, small, episodes = self.setup_two(conn, now)
        for index, episode in enumerate(episodes[:5]):
            request_episode(conn, big, episode.id, now + timedelta(seconds=index), NO_CAP)
        request_episode(conn, small, episodes[5].id, now + timedelta(seconds=60), NO_CAP)
        order: list[int] = []
        for _ in range(6):
            claimed = claim_next(conn, now + timedelta(minutes=5), NO_CAP)
            assert claimed is not None
            order.append(claimed.id)
        small_position = order.index(episodes[5].id)
        assert small_position == 1  # right after the big visitor's first, not after all five

    def test_a_visitor_already_using_every_slot_waits_for_a_new_one(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        big, small, episodes = self.setup_two(conn, now)
        for index, episode in enumerate(episodes[:5]):
            request_episode(conn, big, episode.id, now + timedelta(seconds=index), NO_CAP)
        for _ in range(3):  # three slots all busy with the big visitor's downloads
            assert claim_next(conn, now + timedelta(minutes=1), NO_CAP) is not None
        request_episode(conn, small, episodes[5].id, now + timedelta(minutes=2), NO_CAP)
        claimed = claim_next(conn, now + timedelta(minutes=3), NO_CAP)
        assert claimed is not None
        assert claimed.id == episodes[5].id

    def test_a_shared_episode_counts_for_whoever_asked_first(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        big, small, episodes = self.setup_two(conn, now)
        request_episode(conn, big, episodes[0].id, now, NO_CAP)
        request_episode(conn, small, episodes[0].id, now + timedelta(seconds=1), NO_CAP)
        request_episode(conn, small, episodes[1].id, now + timedelta(seconds=2), NO_CAP)
        first = claim_next(conn, now + timedelta(minutes=1), NO_CAP)
        assert first is not None
        assert first.id == episodes[0].id
