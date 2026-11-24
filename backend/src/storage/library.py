"""A visitor's library: which series they added, with counts that are only about them.

Series and episodes are shared by everyone. What differs per visitor is the library list and
the counts: "downloaded" means episodes *this* visitor saved (or can save right now), and so on.
"""

import sqlite3
from datetime import datetime

from tsuzuki.storage.records import SeriesSummary
from tsuzuki.storage.rows import series_from_row
from tsuzuki.storage.times import to_text

# Counts for one visitor's view of each series in their library. Episode totals are shared;
# everything else comes from this visitor's own requests.
SUMMARY_SQL = """
SELECT s.*,
  (SELECT COUNT(*) FROM episodes e WHERE e.series_id = s.id) AS total,
  (SELECT COUNT(*) FROM requests r JOIN episodes e ON e.id = r.episode_id
     WHERE e.series_id = s.id AND r.visitor_id = :v
       AND (r.delivered_at IS NOT NULL OR e.status = 'ready')) AS downloaded,
  (SELECT COUNT(*) FROM requests r JOIN episodes e ON e.id = r.episode_id
     WHERE e.series_id = s.id AND r.visitor_id = :v AND r.delivered_at IS NULL
       AND e.status IN ('queued', 'downloading')) AS in_progress,
  (SELECT COUNT(*) FROM requests r JOIN episodes e ON e.id = r.episode_id
     WHERE e.series_id = s.id AND r.visitor_id = :v AND r.delivered_at IS NULL
       AND e.status = 'failed') AS failed
FROM series s JOIN library l ON l.series_id = s.id AND l.visitor_id = :v
"""


def summary_from_row(row: sqlite3.Row) -> SeriesSummary:
    return SeriesSummary(
        series=series_from_row(row),
        total=row["total"],
        downloaded=row["downloaded"],
        in_progress=row["in_progress"],
        failed=row["failed"],
    )


def list_summaries(conn: sqlite3.Connection, visitor_id: int) -> list[SeriesSummary]:
    rows = conn.execute(SUMMARY_SQL + " ORDER BY s.title COLLATE NOCASE", {"v": visitor_id})
    return [summary_from_row(row) for row in rows.fetchall()]


def get_summary(conn: sqlite3.Connection, visitor_id: int, series_id: int) -> SeriesSummary | None:
    """None when the series does not exist or is not in this visitor's library."""
    row = conn.execute(SUMMARY_SQL + " WHERE s.id = :s", {"v": visitor_id, "s": series_id})
    found = row.fetchone()
    return summary_from_row(found) if found else None


def add_to_library(
    conn: sqlite3.Connection, visitor_id: int, series_id: int, now: datetime
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO library (visitor_id, series_id, added_at) VALUES (?, ?, ?)",
        (visitor_id, series_id, to_text(now)),
    )


def in_library(conn: sqlite3.Connection, visitor_id: int, series_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM library WHERE visitor_id = ? AND series_id = ?", (visitor_id, series_id)
    ).fetchone()
    return row is not None


def library_size(conn: sqlite3.Connection, visitor_id: int) -> int:
    row = conn.execute("SELECT COUNT(*) FROM library WHERE visitor_id = ?", (visitor_id,))
    return int(row.fetchone()[0])
