import sqlite3
from datetime import datetime, timedelta

from tests._helpers import make_episodes, make_ready, make_series
from tsuzuki.storage import (
    delete_series,
    get_series,
    get_series_by_url,
    lifecycle,
    list_episodes,
    list_series,
    list_summaries,
    upsert_series,
)


class TestUpsert:
    def test_adds_a_series(self, conn: sqlite3.Connection, now: datetime) -> None:
        series = make_series(conn, now)
        assert series.id > 0
        assert (series.site, series.title) == ("animeheaven", "Sample Show")
        assert get_series(conn, series.id) == series

    def test_same_url_updates_instead_of_duplicating(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        first = make_series(conn, now, title="Old title")
        later = now + timedelta(hours=1)
        second = upsert_series(
            conn, site="animeheaven", url=first.url, title="New title", now=later
        )
        assert second.id == first.id
        assert second.title == "New title"
        assert second.created_at == first.created_at
        assert second.updated_at == later
        assert len(list_series(conn)) == 1

    def test_lookup_by_url(self, conn: sqlite3.Connection, now: datetime) -> None:
        series = make_series(conn, now)
        assert get_series_by_url(conn, series.url) == series
        assert get_series_by_url(conn, "https://nope.example/") is None

    def test_missing_id_gives_none(self, conn: sqlite3.Connection) -> None:
        assert get_series(conn, 999) is None


class TestListing:
    def test_sorted_by_title_ignoring_case(self, conn: sqlite3.Connection, now: datetime) -> None:
        for title in ("blue lock", "Dandadan", "Aot"):
            make_series(conn, now, url=f"https://x.example/{title}", title=title)
        assert [s.title for s in list_series(conn)] == ["Aot", "blue lock", "Dandadan"]


class TestSummaries:
    def test_counts_per_status_group(
        self, conn: sqlite3.Connection, downloads, now: datetime
    ) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now, ("1", "2", "3", "4", "5"))
        make_ready(conn, downloads, series.id, "1", now)  # downloaded
        record, _ = make_ready(conn, downloads, series.id, "2", now)
        lifecycle.deliver(conn, record.id, now)  # still counts as downloaded
        episodes = {e.number: e for e in list_episodes(conn, series.id)}
        lifecycle.queue(conn, episodes["3"].id, now)  # in progress
        lifecycle.queue(conn, episodes["4"].id, now)
        lifecycle.start(conn, episodes["4"].id, now)
        lifecycle.fail(conn, episodes["4"].id, now, "timeout")  # failed

        (summary,) = list_summaries(conn)
        assert summary.series.id == series.id
        assert summary.total == 5
        assert summary.downloaded == 2
        assert summary.in_progress == 1
        assert summary.failed == 1

    def test_series_without_episodes_has_zero_counts(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        make_series(conn, now)
        (summary,) = list_summaries(conn)
        assert (summary.total, summary.downloaded, summary.in_progress, summary.failed) == (0,) * 4


class TestDelete:
    def test_removes_the_series_and_its_episodes(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now)
        assert delete_series(conn, series.id) is True
        assert get_series(conn, series.id) is None
        assert conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0] == 0

    def test_deleting_a_missing_series_says_so(self, conn: sqlite3.Connection) -> None:
        assert delete_series(conn, 12345) is False
