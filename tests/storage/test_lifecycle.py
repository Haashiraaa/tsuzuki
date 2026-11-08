import sqlite3
from datetime import datetime, timedelta

import pytest

from tests._helpers import make_episodes, make_series
from tsuzuki.core.errors import InvalidTransitionError
from tsuzuki.storage import EpisodeStatus, get_episode, lifecycle
from tsuzuki.storage.lifecycle import ALLOWED, can_move

S = EpisodeStatus


def one_episode(conn: sqlite3.Connection, now: datetime) -> int:
    series = make_series(conn, now)
    (episode,) = make_episodes(conn, series.id, now, ("1",))
    return episode.id


def status_of(conn: sqlite3.Connection, episode_id: int) -> EpisodeStatus:
    episode = get_episode(conn, episode_id)
    assert episode is not None
    return episode.status


class TestRules:
    def test_every_status_has_an_entry(self) -> None:
        assert set(ALLOWED) == set(EpisodeStatus)

    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (S.AVAILABLE, S.QUEUED),
            (S.QUEUED, S.DOWNLOADING),
            (S.QUEUED, S.AVAILABLE),
            (S.DOWNLOADING, S.READY),
            (S.DOWNLOADING, S.FAILED),
            (S.DOWNLOADING, S.QUEUED),
            (S.READY, S.DELIVERED),
            (S.READY, S.EXPIRED),
            (S.DELIVERED, S.QUEUED),
            (S.EXPIRED, S.QUEUED),
            (S.FAILED, S.QUEUED),
        ],
    )
    def test_allowed_moves(self, current: EpisodeStatus, target: EpisodeStatus) -> None:
        assert can_move(current, target)

    @pytest.mark.parametrize(
        ("current", "target"),
        [
            (S.AVAILABLE, S.READY),
            (S.AVAILABLE, S.DELIVERED),
            (S.QUEUED, S.READY),
            (S.READY, S.QUEUED),
            (S.READY, S.FAILED),
            (S.DELIVERED, S.EXPIRED),
            (S.FAILED, S.READY),
        ],
    )
    def test_refused_moves(self, current: EpisodeStatus, target: EpisodeStatus) -> None:
        assert not can_move(current, target)


class TestHappyPath:
    def test_available_to_delivered(self, conn: sqlite3.Connection, now: datetime) -> None:
        episode_id = one_episode(conn, now)
        assert lifecycle.queue(conn, episode_id, now).status is S.QUEUED
        started = lifecycle.start(conn, episode_id, now)
        assert (started.status, started.attempts) == (S.DOWNLOADING, 1)

        done = lifecycle.finish(
            conn,
            episode_id,
            now,
            file_path="/d/episode_1.mp4",
            size_bytes=123,
            expires_at=now + timedelta(hours=24),
        )
        assert done.status is S.READY
        assert (done.file_path, done.size_bytes) == ("/d/episode_1.mp4", 123)
        assert done.expires_at == now + timedelta(hours=24)

        delivered = lifecycle.deliver(conn, episode_id, now)
        assert delivered.status is S.DELIVERED
        assert (delivered.file_path, delivered.size_bytes, delivered.expires_at) == (None,) * 3

    def test_expiry_clears_file_info_but_keeps_the_row(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        episode_id = one_episode(conn, now)
        lifecycle.queue(conn, episode_id, now)
        lifecycle.start(conn, episode_id, now)
        lifecycle.finish(conn, episode_id, now, file_path="/d/x.mp4", size_bytes=1, expires_at=now)
        expired = lifecycle.expire(conn, episode_id, now)
        assert expired.status is S.EXPIRED
        assert expired.file_path is None


class TestFailureAndRetry:
    def test_failure_records_the_error(self, conn: sqlite3.Connection, now: datetime) -> None:
        episode_id = one_episode(conn, now)
        lifecycle.queue(conn, episode_id, now)
        lifecycle.start(conn, episode_id, now)
        failed = lifecycle.fail(conn, episode_id, now, "timed out")
        assert (failed.status, failed.error) == (S.FAILED, "timed out")

    def test_queueing_again_clears_the_error_and_attempts(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        episode_id = one_episode(conn, now)
        lifecycle.queue(conn, episode_id, now)
        lifecycle.start(conn, episode_id, now)
        lifecycle.fail(conn, episode_id, now, "timed out")
        again = lifecycle.queue(conn, episode_id, now)
        assert (again.status, again.error, again.attempts) == (S.QUEUED, None, 0)

    def test_a_cut_off_download_goes_back_to_the_queue_and_keeps_its_attempt(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        episode_id = one_episode(conn, now)
        lifecycle.queue(conn, episode_id, now)
        lifecycle.start(conn, episode_id, now)
        back = lifecycle.interrupt(conn, episode_id, now)
        assert (back.status, back.attempts) == (S.QUEUED, 1)
        assert lifecycle.start(conn, episode_id, now).attempts == 2

    def test_cancel_returns_a_waiting_episode_to_available(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        episode_id = one_episode(conn, now)
        lifecycle.queue(conn, episode_id, now)
        assert lifecycle.cancel(conn, episode_id, now).status is S.AVAILABLE

    def test_a_delivered_episode_can_be_fetched_again(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        episode_id = one_episode(conn, now)
        lifecycle.queue(conn, episode_id, now)
        lifecycle.start(conn, episode_id, now)
        lifecycle.finish(conn, episode_id, now, file_path="/d/x", size_bytes=1, expires_at=now)
        lifecycle.deliver(conn, episode_id, now)
        assert lifecycle.queue(conn, episode_id, now).status is S.QUEUED


class TestRefusals:
    def test_illegal_move_is_refused_and_changes_nothing(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        episode_id = one_episode(conn, now)
        with pytest.raises(InvalidTransitionError, match="available to ready"):
            lifecycle.finish(conn, episode_id, now, file_path="/d/x", size_bytes=1, expires_at=now)
        assert status_of(conn, episode_id) is S.AVAILABLE

    def test_unknown_episode(self, conn: sqlite3.Connection, now: datetime) -> None:
        with pytest.raises(InvalidTransitionError, match="does not exist"):
            lifecycle.queue(conn, 999, now)

    def test_cannot_deliver_something_that_is_not_ready(
        self, conn: sqlite3.Connection, now: datetime
    ) -> None:
        episode_id = one_episode(conn, now)
        lifecycle.queue(conn, episode_id, now)
        with pytest.raises(InvalidTransitionError):
            lifecycle.deliver(conn, episode_id, now)
