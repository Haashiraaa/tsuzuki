"""Schema versions. The version lives in SQLite's own ``user_version``; no extra table.

Migrations are the ``NNNN_name.sql`` files in ``migrations/``. They are applied in order, each in
its own transaction together with the version bump, so a failure leaves the database at the last
good version. Never edit a migration that has been released: add a new one.
"""

import re
import sqlite3
from dataclasses import dataclass
from importlib import resources

from tsuzuki.core.errors import StorageError

FILE_PATTERN = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
PACKAGE = "tsuzuki.storage.migrations"


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str


def discover() -> list[Migration]:
    """The bundled migrations, in order. Versions must run 1, 2, 3, ... with no gaps."""
    found: list[Migration] = []
    for entry in resources.files(PACKAGE).iterdir():
        match = FILE_PATTERN.match(entry.name)
        if match:
            text = entry.read_text(encoding="utf-8")
            found.append(Migration(int(match.group(1)), match.group(2), text))
    found.sort(key=lambda m: m.version)
    check_sequence(found)
    return found


def check_sequence(migrations: list[Migration]) -> None:
    for expected, migration in enumerate(migrations, start=1):
        if migration.version != expected:
            raise StorageError(
                f"Migration {migration.version:04d} found where {expected:04d} was expected"
            )


def current_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(conn: sqlite3.Connection, migrations: list[Migration] | None = None) -> int:
    """Apply what is missing and return the resulting version."""
    available = discover() if migrations is None else migrations
    version = current_version(conn)
    if version > len(available):
        raise StorageError(
            f"Database is at version {version} but this Tsuzuki only knows {len(available)}. "
            "It was written by a newer version."
        )
    for migration in available[version:]:
        apply(conn, migration)
    return current_version(conn)


def apply(conn: sqlite3.Connection, migration: Migration) -> None:
    script = f"BEGIN;\n{migration.sql}\nPRAGMA user_version = {migration.version};\nCOMMIT;"
    try:
        conn.executescript(script)
    except sqlite3.Error as exc:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        label = f"{migration.version:04d}_{migration.name}"
        raise StorageError(f"Migration {label} failed: {exc}") from exc
