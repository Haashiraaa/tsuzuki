"""Shared fixtures.

The tests mirror ``backend/src/tsuzuki``: ``tests/storage`` tests ``tsuzuki.storage``, and so on.
Nothing here touches the network, the real home folder or a real database: every test gets a
fresh SQLite file under pytest's temporary folder.
"""

import sqlite3
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

from tsuzuki.storage import open_database

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def now() -> datetime:
    """A fixed moment, so tests never depend on the clock."""
    return NOW


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    """A migrated database in a temporary file (a real file, so WAL mode is the real thing)."""
    connection = open_database(tmp_path / "test.db")
    yield connection
    connection.close()


@pytest.fixture
def downloads(tmp_path: Path) -> Path:
    """An empty downloads folder."""
    folder = tmp_path / "Downloads"
    folder.mkdir()
    return folder
