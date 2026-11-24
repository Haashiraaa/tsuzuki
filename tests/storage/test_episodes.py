import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tests._helpers import make_episodes, make_ready, make_series
from tsuzuki.storage import (
    EpisodeStatus,
    count_by_status,
    due_for_expiry,
    find_episode,
    get_episode,
    lifecycle,
    list_by_status,
    list_episodes,
    ready_bytes,
    sync_episodes,
)
from tsuzuki.storage.episodes import ordinal_for


class TestOrdinal:
    @pytest.mark.parametrize(
        ("number", "expected"), [("5", 5.0), ("05", 5.0), ("12.5", 12.5), (" 7 ", 7.0)]
    )
    def test_numeric_numbers_sort_by_value(self, number: str, expected: float) -> None:
        assert ordinal_for(number, position=99) == expected

    def test_other_labels_fall_back_to_their_place_on_the_page(self) -> None:
        assert ordinal_for("SP1", position=3) == 3.0


class TestSync:
    def test_new_episodes_start_available(self, conn: sqlite3.Connection, now: datetime) -> None:
        series = make_series(conn, now)
        added = sync_episodes(conn, series.id, [("2", "r2"), ("1", "r1")], now)
        assert added == 2
        assert {e.status for e in list_episodes(conn, series.id)} == {EpisodeStatus.AVAILABLE}

    def test_syncing_again_adds_only_the_new_ones(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        series = make_series(conn, now)
        sync_episodes(conn, series.id, [("1", "r1")], now)
        added = sync_episodes(conn, series.id, [("2", "r2"), ("1", "r1")], now)
        assert added == 1

    def test_known_episodes_keep_their_status_but_get_a_fresh_ref(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        series = make_series(conn, now)
        (episode,) = make_episodes(conn, series.id, now, ("1",))
        lifecycle.queue(conn, episode.id, now)
        sync_episodes(conn, series.id, [("1", "new-ref")], now)
        again = get_episode(conn, episode.id)
        assert again is not None
        assert (again.status, again.ref) == (EpisodeStatus.QUEUED, "new-ref")


class TestListing:
    def test_orders_by_number_not_by_text(self, conn: sqlite3.Connection, now: datetime) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now, ("9", "10", "11"))
        newest = [e.number for e in list_episodes(conn, series.id, newest_first=True)]
        oldest = [e.number for e in list_episodes(conn, series.id, newest_first=False)]
        assert newest == ["11", "10", "9"]
        assert oldest == ["9", "10", "11"]

    def test_limit(self, conn: sqlite3.Connection, now: datetime) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now, ("1", "2", "3", "4"))
        assert [e.number for e in list_episodes(conn, series.id, limit=2)] == ["4", "3"]

    def test_find_by_number(self, conn: sqlite3.Connection, now: datetime) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now)
        found = find_episode(conn, series.id, "2")
        assert found is not None and found.number == "2"
        assert find_episode(conn, series.id, "99") is None
        assert get_episode(conn, 424242) is None

    def test_by_status(self, conn: sqlite3.Connection, now: datetime) -> None:
        series = make_series(conn, now)
        one, two, _ = make_episodes(conn, series.id, now)
        lifecycle.queue(conn, one.id, now)
        lifecycle.queue(conn, two.id, now + timedelta(minutes=1))
        queued = list_by_status(conn, [EpisodeStatus.QUEUED])
        assert [e.id for e in queued] == [one.id, two.id]  # first in, first out
        assert list_by_status(conn, [EpisodeStatus.FAILED]) == []


class TestDiskAccounting:
    def test_ready_bytes_counts_only_waiting_files(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now)
        make_ready(conn, downloads, series.id, "1", now, content=b"a" * 10)
        record, _ = make_ready(conn, downloads, series.id, "2", now, content=b"b" * 5)
        assert ready_bytes(conn) == 15
        lifecycle.deliver(conn, record.id, now)
        assert ready_bytes(conn) == 10

    def test_due_for_expiry_only_lists_overdue_ready_files(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now)
        old, _ = make_ready(conn, downloads, series.id, "1", now, ttl=timedelta(hours=1))
        make_ready(conn, downloads, series.id, "2", now, ttl=timedelta(hours=48))
        assert due_for_expiry(conn, now) == []
        later = now + timedelta(hours=2)
        assert [e.id for e in due_for_expiry(conn, later)] == [old.id]

    def test_count_by_status(self, conn: sqlite3.Connection, now: datetime) -> None:
        series = make_series(conn, now)
        one, *_ = make_episodes(conn, series.id, now)
        lifecycle.queue(conn, one.id, now)
        assert count_by_status(conn) == {EpisodeStatus.AVAILABLE: 2, EpisodeStatus.QUEUED: 1}
