"""Series: add, find, delete. Shared by everyone; see ``library`` for one visitor's view."""

import sqlite3
from datetime import datetime

from tsuzuki.core.errors import StorageError
from tsuzuki.storage.records import SeriesRecord
from tsuzuki.storage.rows import series_from_row
from tsuzuki.storage.times import to_text


def upsert_series(
    conn: sqlite3.Connection, *, site: str, url: str, title: str, now: datetime
) -> SeriesRecord:
    """Add a series, or refresh the title and site of one with the same URL."""
    stamp = to_text(now)
    conn.execute(
        "INSERT INTO series (site, url, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(url) DO UPDATE SET site = excluded.site, title = excluded.title, "
        "updated_at = excluded.updated_at",
        (site, url, title, stamp, stamp),
    )
    found = get_series_by_url(conn, url)
    if found is None:
        raise StorageError(f"Series vanished right after saving: {url}")
    return found


def get_series(conn: sqlite3.Connection, series_id: int) -> SeriesRecord | None:
    row = conn.execute("SELECT * FROM series WHERE id = ?", (series_id,)).fetchone()
    return series_from_row(row) if row else None


def get_series_by_url(conn: sqlite3.Connection, url: str) -> SeriesRecord | None:
    row = conn.execute("SELECT * FROM series WHERE url = ?", (url,)).fetchone()
    return series_from_row(row) if row else None


def list_series(conn: sqlite3.Connection) -> list[SeriesRecord]:
    rows = conn.execute("SELECT * FROM series ORDER BY title COLLATE NOCASE").fetchall()
    return [series_from_row(row) for row in rows]


def delete_series(conn: sqlite3.Connection, series_id: int) -> bool:
    """Remove a series and its episode rows. Files on disk are not touched here."""
    return conn.execute("DELETE FROM series WHERE id = ?", (series_id,)).rowcount > 0
