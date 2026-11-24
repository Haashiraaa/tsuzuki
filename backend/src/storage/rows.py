"""Turning database rows into records. The only place that knows column names and types."""

import sqlite3

from tsuzuki.storage.records import EpisodeRecord, EpisodeStatus, SeriesRecord
from tsuzuki.storage.times import from_text


def series_from_row(row: sqlite3.Row) -> SeriesRecord:
    return SeriesRecord(
        id=row["id"],
        site=row["site"],
        url=row["url"],
        title=row["title"],
        created_at=from_text(row["created_at"]),
        updated_at=from_text(row["updated_at"]),
    )


def episode_from_row(row: sqlite3.Row) -> EpisodeRecord:
    expires = row["expires_at"]
    return EpisodeRecord(
        id=row["id"],
        series_id=row["series_id"],
        number=row["number"],
        ordinal=row["ordinal"],
        ref=row["ref"],
        status=EpisodeStatus(row["status"]),
        file_path=row["file_path"],
        size_bytes=row["size_bytes"],
        error=row["error"],
        attempts=row["attempts"],
        expires_at=from_text(expires) if expires else None,
        updated_at=from_text(row["updated_at"]),
    )
