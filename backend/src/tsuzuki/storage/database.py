"""Opening the SQLite file and running work inside a transaction.

A connection belongs to one thread. Give each worker thread its own (``open_database`` is cheap).
WAL mode lets readers and one writer work at the same time; ``busy_timeout`` makes a second
writer wait instead of failing at once.
"""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from tsuzuki.core.errors import StorageError
from tsuzuki.storage.migrate import migrate

BUSY_TIMEOUT_MS = 10_000


def connect(path: Path | str) -> sqlite3.Connection:
    """A configured connection. ``isolation_level=None`` so ``transaction`` is in charge."""
    try:
        conn = sqlite3.connect(str(path), timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None)
    except sqlite3.Error as exc:
        raise StorageError(f"Cannot open database {path}: {exc}") from exc
    conn.row_factory = sqlite3.Row
    configure(conn)
    return conn


def configure(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")


def open_database(path: Path | str) -> sqlite3.Connection:
    """Create the folder if needed, connect, and bring the schema up to date."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    migrate(conn)
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[sqlite3.Connection]:
    """All-or-nothing block. ``BEGIN IMMEDIATE`` takes the write lock up front."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
