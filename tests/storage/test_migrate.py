import sqlite3

import pytest

from tsuzuki.core.errors import StorageError
from tsuzuki.storage.database import connect
from tsuzuki.storage.migrate import (
    FILE_PATTERN,
    Migration,
    check_sequence,
    current_version,
    discover,
    migrate,
)


def tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


class TestDiscover:
    def test_finds_the_bundled_migrations_in_order(self) -> None:
        found = discover()
        assert [m.version for m in found] == list(range(1, len(found) + 1))
        assert found[0].name == "initial"
        assert "CREATE TABLE series" in found[0].sql

    def test_file_names_must_be_numbered(self) -> None:
        assert FILE_PATTERN.match("0002_add_notes.sql")
        assert FILE_PATTERN.match("2_add_notes.sql") is None
        assert FILE_PATTERN.match("0002_Add-Notes.sql") is None
        assert FILE_PATTERN.match("__init__.py") is None

    def test_a_gap_in_the_numbers_is_refused(self) -> None:
        with pytest.raises(StorageError, match="0003"):
            check_sequence([Migration(1, "a", ""), Migration(3, "c", "")])


class TestMigrate:
    def test_fresh_database_reaches_the_latest_version(self) -> None:
        conn = connect(":memory:")
        version = migrate(conn)
        assert version == len(discover())
        assert {"series", "episodes"} <= tables(conn)

    def test_running_twice_changes_nothing(self) -> None:
        conn = connect(":memory:")
        first = migrate(conn)
        assert migrate(conn) == first

    def test_database_from_a_newer_version_is_refused(self) -> None:
        conn = connect(":memory:")
        conn.execute("PRAGMA user_version = 99")
        with pytest.raises(StorageError, match="newer"):
            migrate(conn)

    def test_only_missing_migrations_are_applied(self) -> None:
        conn = connect(":memory:")
        first = Migration(1, "first", "CREATE TABLE a (x INTEGER);")
        migrate(conn, [first])
        second = Migration(2, "second", "CREATE TABLE b (x INTEGER);")
        assert migrate(conn, [first, second]) == 2
        assert {"a", "b"} <= tables(conn)

    def test_failed_migration_rolls_back_and_keeps_the_old_version(self) -> None:
        conn = connect(":memory:")
        good = Migration(1, "good", "CREATE TABLE a (x INTEGER);")
        bad = Migration(2, "bad", "CREATE TABLE b (x INTEGER); THIS IS NOT SQL;")
        with pytest.raises(StorageError, match="0002_bad"):
            migrate(conn, [good, bad])
        assert current_version(conn) == 1
        assert "b" not in tables(conn)
        assert not conn.in_transaction
