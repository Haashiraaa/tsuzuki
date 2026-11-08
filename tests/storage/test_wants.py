import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from tests._helpers import make_library, make_ready, make_visitor
from tsuzuki.storage import (
    EpisodeRecord,
    EpisodeStatus,
    RetentionPolicy,
    add_to_library,
    cancel_request,
    confirm_visitor_delivery,
    get_episode,
    get_request,
    lifecycle,
    open_count,
    open_rows,
    request_episode,
    requests_for_series,
    view_status,
)

POLICY = RetentionPolicy()
S = EpisodeStatus


def status(conn: sqlite3.Connection, episode_id: int) -> EpisodeStatus:
    record = get_episode(conn, episode_id)
    assert record is not None
    return record.status


def first_episode(conn: sqlite3.Connection, now: datetime) -> tuple[int, EpisodeRecord]:
    visitor, _ = make_visitor(conn, now)
    _series, episodes = make_library(conn, visitor, now)
    return visitor, episodes[0]


class TestRequesting:
    def test_asking_creates_a_request_and_queues_the_episode(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        visitor, episode = first_episode(conn, now)
        assert request_episode(conn, visitor, episode.id, now, POLICY) is True
        assert status(conn, episode.id) is S.QUEUED
        request = get_request(conn, visitor, episode.id)
        assert request is not None
        assert request.delivered_at is None

    def test_asking_again_changes_nothing(self, conn: sqlite3.Connection, now: datetime) -> None:
        visitor, episode = first_episode(conn, now)
        request_episode(conn, visitor, episode.id, now, POLICY)
        assert request_episode(conn, visitor, episode.id, now, POLICY) is False
        assert open_count(conn, visitor) == 1

    def test_two_visitors_asking_for_one_episode_cause_one_download(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        first, episode = first_episode(conn, now)
        second, _ = make_visitor(conn, now)
        add_to_library(conn, second, episode.series_id, now)
        request_episode(conn, first, episode.id, now, POLICY)
        request_episode(conn, second, episode.id, now, POLICY)
        assert status(conn, episode.id) is S.QUEUED
        assert conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0] == 2

    def test_asking_for_a_ready_file_pushes_its_deadline_back(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        first, episode = first_episode(conn, now)
        second, _ = make_visitor(conn, now)
        add_to_library(conn, second, episode.series_id, now)
        request_episode(conn, first, episode.id, now, POLICY)
        conn.execute("UPDATE episodes SET status = 'available' WHERE id = ?", (episode.id,))
        record, _path = make_ready(
            conn, downloads, episode.series_id, episode.number, now, ttl=timedelta(hours=1)
        )
        later = now + timedelta(minutes=50)
        request_episode(conn, second, record.id, later, POLICY)
        refreshed = get_episode(conn, record.id)
        assert refreshed is not None
        assert refreshed.expires_at == later + POLICY.ttl

    def test_a_saved_episode_can_be_asked_for_again(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        visitor, episode = first_episode(conn, now)
        request_episode(conn, visitor, episode.id, now, POLICY)
        lifecycle.start(conn, episode.id, now)
        path = downloads / "e.mp4"
        path.write_bytes(b"x")
        lifecycle.finish(conn, episode.id, now, file_path=str(path), size_bytes=1, expires_at=now)
        confirm_visitor_delivery(conn, downloads, visitor, episode.id, now)
        assert status(conn, episode.id) is S.DELIVERED
        assert request_episode(conn, visitor, episode.id, now, POLICY) is True
        assert status(conn, episode.id) is S.QUEUED
        request = get_request(conn, visitor, episode.id)
        assert request is not None
        assert request.delivered_at is None


class TestWhatEachVisitorSees:
    def test_delivered_is_personal(self, conn: sqlite3.Connection, now: datetime) -> None:
        visitor, episode = first_episode(conn, now)
        request_episode(conn, visitor, episode.id, now, POLICY)
        mine = get_request(conn, visitor, episode.id)
        assert view_status(S.READY, mine) is S.READY
        assert view_status(S.READY, None) is S.AVAILABLE

    def test_requests_for_a_series_are_only_this_visitors(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        first, episode = first_episode(conn, now)
        second, _ = make_visitor(conn, now)
        request_episode(conn, first, episode.id, now, POLICY)
        assert set(requests_for_series(conn, first, episode.series_id)) == {episode.id}
        assert requests_for_series(conn, second, episode.series_id) == {}

    def test_open_rows_lists_only_my_unsaved_requests_oldest_first(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        visitor, _ = make_visitor(conn, now)
        other, _ = make_visitor(conn, now)
        _series, episodes = make_library(conn, visitor, now)
        add_to_library(conn, other, _series.id, now)
        request_episode(conn, visitor, episodes[1].id, now, POLICY)
        request_episode(conn, visitor, episodes[0].id, now + timedelta(seconds=1), POLICY)
        request_episode(conn, other, episodes[2].id, now, POLICY)
        rows = open_rows(conn, visitor)
        assert [r.episode.id for r in rows] == [episodes[1].id, episodes[0].id]
        assert rows[0].series_title == "Sample Show"

    def test_open_count_only_counts_episodes_still_waiting(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        visitor, _ = make_visitor(conn, now)
        _series, episodes = make_library(conn, visitor, now)
        for episode in episodes:
            request_episode(conn, visitor, episode.id, now, POLICY)
        assert open_count(conn, visitor) == 3
        lifecycle.start(conn, episodes[0].id, now)
        lifecycle.fail(conn, episodes[0].id, now, "boom")
        assert open_count(conn, visitor) == 2


class TestCancel:
    def test_a_waiting_episode_nobody_else_wants_goes_back_to_the_library(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        visitor, episode = first_episode(conn, now)
        request_episode(conn, visitor, episode.id, now, POLICY)
        assert cancel_request(conn, visitor, episode.id, now) is False
        assert status(conn, episode.id) is S.AVAILABLE
        assert get_request(conn, visitor, episode.id) is None

    def test_a_waiting_episode_someone_else_wants_stays_queued(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        first, episode = first_episode(conn, now)
        second, _ = make_visitor(conn, now)
        add_to_library(conn, second, episode.series_id, now)
        request_episode(conn, first, episode.id, now, POLICY)
        request_episode(conn, second, episode.id, now, POLICY)
        cancel_request(conn, first, episode.id, now)
        assert status(conn, episode.id) is S.QUEUED
        assert get_request(conn, second, episode.id) is not None

    def test_a_running_download_nobody_else_wants_should_be_stopped(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        visitor, episode = first_episode(conn, now)
        request_episode(conn, visitor, episode.id, now, POLICY)
        lifecycle.start(conn, episode.id, now)
        assert cancel_request(conn, visitor, episode.id, now) is True

    def test_a_running_download_someone_else_wants_keeps_going(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        first, episode = first_episode(conn, now)
        second, _ = make_visitor(conn, now)
        add_to_library(conn, second, episode.series_id, now)
        request_episode(conn, first, episode.id, now, POLICY)
        request_episode(conn, second, episode.id, now, POLICY)
        lifecycle.start(conn, episode.id, now)
        assert cancel_request(conn, first, episode.id, now) is False
        assert status(conn, episode.id) is S.DOWNLOADING


class TestDelivery:
    def ready_for(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime, count: int
    ) -> tuple[list[int], int, Path]:
        visitors = [make_visitor(conn, now)[0] for _ in range(count)]
        series, episodes = make_library(conn, visitors[0], now)
        for visitor in visitors[1:]:
            add_to_library(conn, visitor, series.id, now)
        episode = episodes[0]
        for visitor in visitors:
            request_episode(conn, visitor, episode.id, now, POLICY)
        lifecycle.start(conn, episode.id, now)
        path = downloads / "shared.mp4"
        path.write_bytes(b"video")
        lifecycle.finish(
            conn, episode.id, now, file_path=str(path), size_bytes=5, expires_at=now + POLICY.ttl
        )
        return visitors, episode.id, path

    def test_the_file_stays_until_the_last_visitor_has_saved_it(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        visitors, episode_id, path = self.ready_for(conn, downloads, now, 3)
        assert confirm_visitor_delivery(conn, downloads, visitors[0], episode_id, now) is False
        assert confirm_visitor_delivery(conn, downloads, visitors[1], episode_id, now) is False
        assert path.exists()
        assert status(conn, episode_id) is S.READY
        assert confirm_visitor_delivery(conn, downloads, visitors[2], episode_id, now) is True
        assert not path.exists()
        assert status(conn, episode_id) is S.DELIVERED

    def test_each_visitor_sees_their_own_saved_state(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        visitors, episode_id, _path = self.ready_for(conn, downloads, now, 2)
        confirm_visitor_delivery(conn, downloads, visitors[0], episode_id, now)
        first = get_request(conn, visitors[0], episode_id)
        second = get_request(conn, visitors[1], episode_id)
        assert first is not None
        assert second is not None
        assert first.delivered_at is not None
        assert second.delivered_at is None

    def test_saving_twice_is_harmless(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        visitors, episode_id, path = self.ready_for(conn, downloads, now, 2)
        confirm_visitor_delivery(conn, downloads, visitors[0], episode_id, now)
        confirm_visitor_delivery(conn, downloads, visitors[0], episode_id, now)
        assert path.exists()
