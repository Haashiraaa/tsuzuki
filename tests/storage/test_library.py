import sqlite3
from datetime import datetime
from pathlib import Path

from tests._helpers import make_library, make_series, make_visitor
from tsuzuki.storage import (
    RetentionPolicy,
    add_to_library,
    confirm_visitor_delivery,
    get_summary,
    in_library,
    library_size,
    lifecycle,
    list_summaries,
    request_episode,
)

POLICY = RetentionPolicy()


def test_a_visitor_only_sees_their_own_series(conn: sqlite3.Connection, now: datetime) -> None:
    mine, _ = make_visitor(conn, now)
    theirs, _ = make_visitor(conn, now)
    make_library(conn, mine, now, url="https://animeheaven.me/anime.php?a", title="Mine")
    make_library(conn, theirs, now, url="https://animeheaven.me/anime.php?b", title="Theirs")
    assert [s.series.title for s in list_summaries(conn, mine)] == ["Mine"]
    assert [s.series.title for s in list_summaries(conn, theirs)] == ["Theirs"]


def test_two_visitors_can_share_a_series(conn: sqlite3.Connection, now: datetime) -> None:
    first, _ = make_visitor(conn, now)
    second, _ = make_visitor(conn, now)
    series, _ = make_library(conn, first, now)
    add_to_library(conn, second, series.id, now)
    assert in_library(conn, second, series.id)
    assert library_size(conn, second) == 1
    assert conn.execute("SELECT COUNT(*) FROM series").fetchone()[0] == 1


def test_adding_twice_changes_nothing(conn: sqlite3.Connection, now: datetime) -> None:
    visitor, _ = make_visitor(conn, now)
    series, _ = make_library(conn, visitor, now)
    add_to_library(conn, visitor, series.id, now)
    assert library_size(conn, visitor) == 1


def test_a_series_outside_the_library_has_no_summary(
    conn: sqlite3.Connection, now: datetime
) -> None:
    visitor, _ = make_visitor(conn, now)
    series = make_series(conn, now)
    assert get_summary(conn, visitor, series.id) is None


def finish_with_file(
    conn: sqlite3.Connection, downloads: Path, episode_id: int, now: datetime
) -> None:
    lifecycle.start(conn, episode_id, now)
    path = downloads / f"episode_{episode_id}.mp4"
    path.write_bytes(b"x")
    lifecycle.finish(conn, episode_id, now, file_path=str(path), size_bytes=1, expires_at=now)


def test_counts_are_personal(conn: sqlite3.Connection, downloads: Path, now: datetime) -> None:
    me, _ = make_visitor(conn, now)
    other, _ = make_visitor(conn, now)
    series, listed = make_library(conn, me, now, numbers=("1", "2", "3", "4", "5"))
    add_to_library(conn, other, series.id, now)
    episodes = {e.number: e for e in listed}
    for number in "1234":
        request_episode(conn, me, episodes[number].id, now, POLICY)

    finish_with_file(conn, downloads, episodes["1"].id, now)  # ready, not saved yet
    finish_with_file(conn, downloads, episodes["2"].id, now)
    confirm_visitor_delivery(conn, downloads, me, episodes["2"].id, now)  # saved
    lifecycle.start(conn, episodes["3"].id, now)  # still downloading
    lifecycle.start(conn, episodes["4"].id, now)
    lifecycle.fail(conn, episodes["4"].id, now, "timeout")

    mine = get_summary(conn, me, series.id)
    theirs = get_summary(conn, other, series.id)
    assert mine is not None
    assert theirs is not None
    assert (mine.total, mine.downloaded, mine.in_progress, mine.failed) == (5, 2, 1, 1)
    assert (theirs.total, theirs.downloaded, theirs.in_progress, theirs.failed) == (5, 0, 0, 0)
