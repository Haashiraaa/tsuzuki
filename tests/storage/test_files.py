import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tests._helpers import make_episodes, make_ready, make_series
from tsuzuki.core.errors import InvalidTransitionError, StorageError
from tsuzuki.storage import (
    EpisodeStatus,
    confirm_delivery,
    get_episode,
    remove_file,
    sweep_expired,
)


class TestRemoveFile:
    def test_deletes_a_file_inside_the_root(self, downloads: Path) -> None:
        target = downloads / "episode_1.mp4"
        target.write_bytes(b"x")
        assert remove_file(downloads, str(target)) is True
        assert not target.exists()

    def test_a_missing_file_is_not_an_error(self, downloads: Path) -> None:
        assert remove_file(downloads, str(downloads / "gone.mp4")) is False

    def test_no_path_means_nothing_to_do(self, downloads: Path) -> None:
        assert remove_file(downloads, None) is False
        assert remove_file(downloads, "") is False

    def test_refuses_a_file_outside_the_root(self, downloads: Path, tmp_path: Path) -> None:
        outside = tmp_path / "precious.txt"
        outside.write_text("keep me")
        with pytest.raises(StorageError, match="outside"):
            remove_file(downloads, str(outside))
        assert outside.exists()

    def test_refuses_a_path_that_climbs_out(self, downloads: Path, tmp_path: Path) -> None:
        outside = tmp_path / "precious.txt"
        outside.write_text("keep me")
        sneaky = downloads / ".." / "precious.txt"
        with pytest.raises(StorageError):
            remove_file(downloads, str(sneaky))
        assert outside.exists()


class TestConfirmDelivery:
    def test_removes_the_file_and_keeps_the_record(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now)
        record, path = make_ready(conn, downloads, series.id, "1", now)
        done = confirm_delivery(conn, downloads, record.id, now)
        assert done.status is EpisodeStatus.DELIVERED
        assert not path.exists()
        assert get_episode(conn, record.id) is not None

    def test_a_file_that_is_not_ready_is_left_alone(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        series = make_series(conn, now)
        (episode, *_) = make_episodes(conn, series.id, now)
        bystander = downloads / "episode_1.mp4"
        bystander.write_bytes(b"x")
        with pytest.raises(InvalidTransitionError):
            confirm_delivery(conn, downloads, episode.id, now)
        assert bystander.exists()

    def test_delivering_twice_is_refused(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now)
        record, _ = make_ready(conn, downloads, series.id, "1", now)
        confirm_delivery(conn, downloads, record.id, now)
        with pytest.raises(InvalidTransitionError):
            confirm_delivery(conn, downloads, record.id, now)


class TestSweepExpired:
    def test_removes_only_files_past_their_time(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now)
        old, old_path = make_ready(conn, downloads, series.id, "1", now, ttl=timedelta(hours=1))
        fresh, fresh_path = make_ready(
            conn, downloads, series.id, "2", now, ttl=timedelta(hours=48)
        )

        expired = sweep_expired(conn, downloads, now + timedelta(hours=2))

        assert [e.id for e in expired] == [old.id]
        assert expired[0].status is EpisodeStatus.EXPIRED
        assert not old_path.exists()
        assert fresh_path.exists()
        stored = get_episode(conn, fresh.id)
        assert stored is not None and stored.status is EpisodeStatus.READY

    def test_a_second_sweep_finds_nothing(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now)
        make_ready(conn, downloads, series.id, "1", now, ttl=timedelta(hours=1))
        later = now + timedelta(hours=2)
        assert len(sweep_expired(conn, downloads, later)) == 1
        assert sweep_expired(conn, downloads, later) == []

    def test_a_file_already_deleted_by_hand_still_expires_cleanly(
        self, conn: sqlite3.Connection, downloads: Path, now: datetime
    ) -> None:
        series = make_series(conn, now)
        make_episodes(conn, series.id, now)
        _, path = make_ready(conn, downloads, series.id, "1", now, ttl=timedelta(hours=1))
        path.unlink()
        (record,) = sweep_expired(conn, downloads, now + timedelta(hours=2))
        assert record.status is EpisodeStatus.EXPIRED
