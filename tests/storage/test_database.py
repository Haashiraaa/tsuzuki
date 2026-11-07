import sqlite3
from pathlib import Path

import pytest

from tsuzuki.storage import open_database, transaction


class TestOpenDatabase:
    def test_creates_missing_folders(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "er" / "tsuzuki.db"
        conn = open_database(path)
        conn.close()
        assert path.is_file()

    def test_uses_wal_and_enforces_foreign_keys(self, conn: sqlite3.Connection) -> None:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_reopening_keeps_the_data(self, tmp_path: Path) -> None:
        path = tmp_path / "t.db"
        first = open_database(path)
        first.execute(
            "INSERT INTO series (site, url, title, created_at, updated_at) "
            "VALUES ('s', 'u', 't', 'x', 'x')"
        )
        first.close()
        second = open_database(path)
        assert second.execute("SELECT COUNT(*) FROM series").fetchone()[0] == 1


class TestTransaction:
    def test_commits_when_the_block_succeeds(self, conn: sqlite3.Connection) -> None:
        with transaction(conn):
            conn.execute(
                "INSERT INTO series (site, url, title, created_at, updated_at) "
                "VALUES ('s', 'u', 't', 'x', 'x')"
            )
        assert not conn.in_transaction
        assert conn.execute("SELECT COUNT(*) FROM series").fetchone()[0] == 1

    def test_rolls_back_when_the_block_raises(self, conn: sqlite3.Connection) -> None:
        with pytest.raises(RuntimeError), transaction(conn):
            conn.execute(
                "INSERT INTO series (site, url, title, created_at, updated_at) "
                "VALUES ('s', 'u', 't', 'x', 'x')"
            )
            raise RuntimeError("boom")
        assert not conn.in_transaction
        assert conn.execute("SELECT COUNT(*) FROM series").fetchone()[0] == 0
