"""Series: add, find, list with counts, delete."""

import sqlite3
from datetime import datetime

from tsuzuki.core.errors import StorageError
from tsuzuki.storage.records import (
    DOWNLOADED,
    IN_PROGRESS,
    EpisodeStatus,
    SeriesRecord,
    SeriesSummary,
)
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


def list_summaries(conn: sqlite3.Connection) -> list[SeriesSummary]:
    counts = status_counts_by_series(conn)
    return [summarize(series, counts.get(series.id, {})) for series in list_series(conn)]


def status_counts_by_series(conn: sqlite3.Connection) -> dict[int, dict[EpisodeStatus, int]]:
    rows = conn.execute(
        "SELECT series_id, status, COUNT(*) AS n FROM episodes GROUP BY series_id, status"
    ).fetchall()
    counts: dict[int, dict[EpisodeStatus, int]] = {}
    for row in rows:
        counts.setdefault(row["series_id"], {})[EpisodeStatus(row["status"])] = row["n"]
    return counts


def summarize(series: SeriesRecord, counts: dict[EpisodeStatus, int]) -> SeriesSummary:
    return SeriesSummary(
        series=series,
        total=sum(counts.values()),
        downloaded=sum(n for status, n in counts.items() if status in DOWNLOADED),
        in_progress=sum(n for status, n in counts.items() if status in IN_PROGRESS),
        failed=counts.get(EpisodeStatus.FAILED, 0),
    )


def delete_series(conn: sqlite3.Connection, series_id: int) -> bool:
    """Remove a series and its episode rows. Files on disk are not touched here."""
    return conn.execute("DELETE FROM series WHERE id = ?", (series_id,)).rowcount > 0
