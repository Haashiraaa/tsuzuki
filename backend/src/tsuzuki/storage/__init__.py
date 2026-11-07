"""Local storage in one SQLite file: series, episodes and what became of each download.

Typical use::

    conn = open_database(root.database)
    with transaction(conn):
        series = upsert_series(conn, site="animeheaven", url=url, title=title, now=utc_now())
        sync_episodes(conn, series.id, [(e.number, e.ref) for e in listed], utc_now())
"""

from tsuzuki.storage.database import connect, open_database, transaction
from tsuzuki.storage.episodes import (
    count_by_status,
    due_for_expiry,
    find_episode,
    get_episode,
    list_by_status,
    list_episodes,
    ready_bytes,
    sync_episodes,
)
from tsuzuki.storage.files import confirm_delivery, remove_file, sweep_expired
from tsuzuki.storage.records import (
    EpisodeRecord,
    EpisodeStatus,
    SeriesRecord,
    SeriesSummary,
)
from tsuzuki.storage.retention import RetentionPolicy, expiry_for, has_room
from tsuzuki.storage.series import (
    delete_series,
    get_series,
    get_series_by_url,
    list_series,
    list_summaries,
    upsert_series,
)
from tsuzuki.storage.times import utc_now

__all__ = [
    "EpisodeRecord",
    "EpisodeStatus",
    "RetentionPolicy",
    "SeriesRecord",
    "SeriesSummary",
    "confirm_delivery",
    "connect",
    "count_by_status",
    "delete_series",
    "due_for_expiry",
    "expiry_for",
    "find_episode",
    "get_episode",
    "get_series",
    "get_series_by_url",
    "has_room",
    "list_by_status",
    "list_episodes",
    "list_series",
    "list_summaries",
    "open_database",
    "ready_bytes",
    "remove_file",
    "sweep_expired",
    "sync_episodes",
    "transaction",
    "upsert_series",
    "utc_now",
]
