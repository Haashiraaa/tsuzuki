import time
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from tests._helpers import make_episodes, make_series
from tests.worker.conftest import FakeDownloader, make_services, make_settings, queued_episode
from tsuzuki.core.progress import ProgressBoard
from tsuzuki.storage import (
    EpisodeStatus,
    RetentionPolicy,
    connect,
    get_episode,
    lifecycle,
    open_database,
)
from tsuzuki.worker import WorkerPool, WorkerSettings


def wait_until(condition: Callable[[], bool], seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.02)
    return False


def statuses(settings: WorkerSettings, ids: list[int]) -> list[EpisodeStatus]:
    conn = connect(settings.database)
    try:
        found = [get_episode(conn, episode_id) for episode_id in ids]
    finally:
        conn.close()
    return [record.status for record in found if record is not None]


def test_the_pool_runs_every_queued_episode(
    downloads: Path, tmp_path: Path, board: ProgressBoard, now: datetime
) -> None:
    settings = make_settings(tmp_path, downloads, slots=2)
    conn = open_database(settings.database)
    series = make_series(conn, now)
    make_episodes(conn, series.id, now, ("1", "2", "3", "4", "5"))
    ids = [queued_episode(conn, series.id, str(n), now) for n in range(1, 6)]
    conn.close()

    pool = WorkerPool(settings, make_services(FakeDownloader(), board, now))
    pool.start()
    try:
        assert wait_until(lambda: statuses(settings, ids) == [EpisodeStatus.READY] * 5)
    finally:
        pool.stop()
    assert len(list((downloads / "Sample-Show").glob("*.mp4"))) == 5


def test_episodes_queued_after_start_are_picked_up(
    downloads: Path, tmp_path: Path, board: ProgressBoard, now: datetime
) -> None:
    settings = make_settings(tmp_path, downloads)
    conn = open_database(settings.database)
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    pool = WorkerPool(settings, make_services(FakeDownloader(), board, now))
    pool.start()
    try:
        late = queued_episode(conn, series.id, "2", now)
        assert wait_until(lambda: statuses(settings, [late]) == [EpisodeStatus.READY])
    finally:
        pool.stop()
        conn.close()


def test_a_download_cut_off_by_a_crash_is_finished_after_a_restart(
    downloads: Path, tmp_path: Path, board: ProgressBoard, now: datetime
) -> None:
    settings = make_settings(tmp_path, downloads)
    conn = open_database(settings.database)
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    stuck = queued_episode(conn, series.id, "1", now)
    lifecycle.start(conn, stuck, now)  # the server died while this was downloading
    conn.close()

    pool = WorkerPool(settings, make_services(FakeDownloader(), board, now))
    pool.start()
    try:
        assert wait_until(lambda: statuses(settings, [stuck]) == [EpisodeStatus.READY])
    finally:
        pool.stop()


def test_a_full_allowance_holds_back_the_rest_of_the_queue(
    downloads: Path, tmp_path: Path, board: ProgressBoard, now: datetime
) -> None:
    base = make_settings(tmp_path, downloads)
    settings = WorkerSettings(
        database=base.database,
        downloads=downloads,
        retention=RetentionPolicy(max_ready_bytes=500),
        slots=1,
        retry=base.retry,
        poll_seconds=0.02,
    )
    conn = open_database(settings.database)
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    first = queued_episode(conn, series.id, "1", now)
    second = queued_episode(conn, series.id, "2", now + timedelta(seconds=1))
    conn.close()

    pool = WorkerPool(settings, make_services(FakeDownloader(size=1000), board, now))
    pool.start()
    try:
        assert wait_until(lambda: statuses(settings, [first])[0] is EpisodeStatus.READY)
        time.sleep(0.3)
        assert statuses(settings, [second]) == [EpisodeStatus.QUEUED]
    finally:
        pool.stop()


def test_stopping_the_pool_puts_a_running_download_back_in_the_queue(
    downloads: Path, tmp_path: Path, board: ProgressBoard, now: datetime
) -> None:
    settings = make_settings(tmp_path, downloads)
    conn = open_database(settings.database)
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    episode = queued_episode(conn, series.id, "1", now)
    conn.close()

    started = {"yes": False}

    def slow(_index: int) -> None:
        started["yes"] = True
        time.sleep(0.2)

    pool = WorkerPool(settings, make_services(FakeDownloader(chunks=10, on_chunk=slow), board, now))
    pool.start()
    assert wait_until(lambda: started["yes"])
    pool.stop()
    assert statuses(settings, [episode]) == [EpisodeStatus.QUEUED]
