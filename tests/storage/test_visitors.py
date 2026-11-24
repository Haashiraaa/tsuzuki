import sqlite3
from datetime import datetime

from tsuzuki.storage import create_visitor, find_visitor
from tsuzuki.storage.visitors import hash_token


def test_a_new_visitor_gets_a_secret_the_server_can_recognise(
    conn: sqlite3.Connection, now: datetime
) -> None:
    visitor_id, token = create_visitor(conn, now)
    assert find_visitor(conn, token) == visitor_id


def test_visitors_are_told_apart(conn: sqlite3.Connection, now: datetime) -> None:
    first, first_token = create_visitor(conn, now)
    second, second_token = create_visitor(conn, now)
    assert first != second
    assert first_token != second_token
    assert find_visitor(conn, second_token) == second


def test_an_unknown_token_is_nobody(conn: sqlite3.Connection) -> None:
    assert find_visitor(conn, "not-a-real-token") is None


def test_the_database_never_holds_the_token_itself(conn: sqlite3.Connection, now: datetime) -> None:
    _id, token = create_visitor(conn, now)
    stored = conn.execute("SELECT token_hash FROM visitors").fetchone()[0]
    assert stored == hash_token(token)
    assert token not in stored
