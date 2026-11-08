import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from tests._helpers import make_episodes, make_series
from tests.worker.conftest import (
    NO_WAIT,
    FakeDownloader,
    FakeSite,
    make_services,
    make_settings,
    queued_episode,
)
from tsuzuki.core.errors import DownloadError, SiteNotSupportedError
from tsuzuki.core.progress import ProgressBoard
from tsuzuki.download.pipeline import Notice
from tsuzuki.storage import EpisodeRecord, EpisodeStatus, RetentionPolicy, claim_next, get_episode
from tsuzuki.worker import run_episode
from tsuzuki.worker.job import ARIA2, BUILT_IN


def claimed(conn: sqlite3.Connection, now: datetime, number: str = "1") -> EpisodeRecord:
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    queued_episode(conn, series.id, number, now)
    record = claim_next(conn, now, RetentionPolicy())
    assert record is not None
    return record


def reload(conn: sqlite3.Connection, record: EpisodeRecord) -> EpisodeRecord:
    found = get_episode(conn, record.id)
    assert found is not None
    return found


def test_a_download_ends_ready_with_its_file_and_deadline(
    conn: sqlite3.Connection,
    downloads: Path,
    tmp_path: Path,
    board: ProgressBoard,
    now: datetime,
) -> None:
    record = claimed(conn, now)
    services = make_services(FakeDownloader(size=2000), board, now)
    run_episode(conn, record, make_settings(tmp_path, downloads), services)
    done = reload(conn, record)
    assert done.status is EpisodeStatus.READY
    assert done.file_path == str(downloads / "Sample-Show" / "episode_1.mp4")
    assert done.size_bytes == 2000
    assert done.file_path is not None
    assert Path(done.file_path).stat().st_size == 2000
    assert done.expires_at == now + timedelta(hours=24)
    assert board.get(record.id) is None


def test_progress_reaches_the_board_while_downloading(
    conn: sqlite3.Connection,
    downloads: Path,
    tmp_path: Path,
    board: ProgressBoard,
    now: datetime,
) -> None:
    record = claimed(conn, now)
    seen: list[tuple[str, int, int]] = []

    def look(_index: int) -> None:
        progress = board.get(record.id)
        assert progress is not None
        seen.append((progress.method, progress.bytes_done, progress.bytes_total))

    downloader = FakeDownloader(size=1000, chunks=2, on_chunk=look)
    run_episode(
        conn, record, make_settings(tmp_path, downloads), make_services(downloader, board, now)
    )
    assert seen[0][0] == ARIA2
    assert seen[1] == (ARIA2, 500, 1000)


def test_the_method_says_built_in_when_aria2_is_missing(
    conn: sqlite3.Connection,
    downloads: Path,
    tmp_path: Path,
    board: ProgressBoard,
    now: datetime,
) -> None:
    record = claimed(conn, now)
    methods: list[str] = []

    def look(_index: int) -> None:
        progress = board.get(record.id)
        assert progress is not None
        methods.append(progress.method)

    downloader = FakeDownloader(on_chunk=look)
    services = make_services(downloader, board, now, hint="install aria2")
    run_episode(conn, record, make_settings(tmp_path, downloads), services)
    assert set(methods) == {BUILT_IN}


def test_a_fall_back_to_the_built_in_downloader_shows_on_the_queue(
    conn: sqlite3.Connection,
    downloads: Path,
    tmp_path: Path,
    board: ProgressBoard,
    now: datetime,
) -> None:
    record = claimed(conn, now)
    notices: list[Notice] = []
    methods: list[str] = []

    def at_chunk(index: int) -> None:
        if index == 1:
            notices[0]("aria2c failed. Falling back to the built-in downloader.")
        progress = board.get(record.id)
        assert progress is not None
        methods.append(progress.method)

    downloader = FakeDownloader(on_chunk=at_chunk)
    services = make_services(downloader, board, now, on_plan=notices.append)
    run_episode(conn, record, make_settings(tmp_path, downloads), services)
    assert methods == [BUILT_IN] * 4


def test_a_failed_download_records_why(
    conn: sqlite3.Connection,
    downloads: Path,
    tmp_path: Path,
    board: ProgressBoard,
    now: datetime,
) -> None:
    record = claimed(conn, now)
    downloader = FakeDownloader(errors=[DownloadError("aria2c exited with code 3")])
    run_episode(
        conn, record, make_settings(tmp_path, downloads), make_services(downloader, board, now)
    )
    failed = reload(conn, record)
    assert failed.status is EpisodeStatus.FAILED
    assert failed.error == "aria2c exited with code 3"
    assert board.get(record.id) is None


def test_a_download_that_fails_once_is_retried(
    conn: sqlite3.Connection,
    downloads: Path,
    tmp_path: Path,
    board: ProgressBoard,
    now: datetime,
) -> None:
    record = claimed(conn, now)
    downloader = FakeDownloader(errors=[DownloadError("hiccup")])
    settings = make_settings(tmp_path, downloads, retry=NO_WAIT)
    run_episode(conn, record, settings, make_services(downloader, board, now))
    assert reload(conn, record).status is EpisodeStatus.READY
    assert downloader.calls == 2


def test_a_site_that_cannot_be_read_fails_the_episode(
    conn: sqlite3.Connection,
    downloads: Path,
    tmp_path: Path,
    board: ProgressBoard,
    now: datetime,
) -> None:
    record = claimed(conn, now)
    site = FakeSite(SiteNotSupportedError("No site adapter for 'x'"))
    services = make_services(FakeDownloader(), board, now, site=site)
    run_episode(conn, record, make_settings(tmp_path, downloads), services)
    failed = reload(conn, record)
    assert failed.status is EpisodeStatus.FAILED
    assert "No site adapter" in (failed.error or "")


def test_a_bug_fails_that_episode_and_not_the_worker(
    conn: sqlite3.Connection,
    downloads: Path,
    tmp_path: Path,
    board: ProgressBoard,
    now: datetime,
) -> None:
    record = claimed(conn, now)
    downloader = FakeDownloader(errors=[RuntimeError("boom")])
    run_episode(
        conn, record, make_settings(tmp_path, downloads), make_services(downloader, board, now)
    )
    failed = reload(conn, record)
    assert failed.status is EpisodeStatus.FAILED
    assert failed.error == "Unexpected error: boom"


def test_cancelling_mid_download_stops_it_and_removes_the_partial_file(
    conn: sqlite3.Connection,
    downloads: Path,
    tmp_path: Path,
    board: ProgressBoard,
    now: datetime,
) -> None:
    record = claimed(conn, now)

    def cancel_after_first_chunk(index: int) -> None:
        if index == 1:
            board.request_cancel(record.id)

    downloader = FakeDownloader(on_chunk=cancel_after_first_chunk)
    run_episode(
        conn, record, make_settings(tmp_path, downloads), make_services(downloader, board, now)
    )
    assert reload(conn, record).status is EpisodeStatus.AVAILABLE
    assert not (downloads / "Sample-Show" / "episode_1.mp4").exists()
    assert not board.cancel_requested(record.id)


def test_cancelling_before_the_download_starts_works_too(
    conn: sqlite3.Connection,
    downloads: Path,
    tmp_path: Path,
    board: ProgressBoard,
    now: datetime,
) -> None:
    record = claimed(conn, now)
    board.request_cancel(record.id)
    downloader = FakeDownloader()
    run_episode(
        conn, record, make_settings(tmp_path, downloads), make_services(downloader, board, now)
    )
    assert reload(conn, record).status is EpisodeStatus.AVAILABLE
    assert downloader.calls == 0


def test_a_server_stop_puts_the_download_back_and_keeps_the_partial_file(
    conn: sqlite3.Connection,
    downloads: Path,
    tmp_path: Path,
    board: ProgressBoard,
    now: datetime,
) -> None:
    record = claimed(conn, now)
    stopping = {"now": False}

    def stop_after_first_chunk(index: int) -> None:
        if index == 1:
            stopping["now"] = True

    downloader = FakeDownloader(on_chunk=stop_after_first_chunk)
    run_episode(
        conn,
        record,
        make_settings(tmp_path, downloads),
        make_services(downloader, board, now),
        should_stop=lambda: stopping["now"],
    )
    assert reload(conn, record).status is EpisodeStatus.QUEUED
    assert (downloads / "Sample-Show" / "episode_1.mp4").exists()
