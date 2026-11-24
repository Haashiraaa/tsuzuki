"""Local storage in one SQLite file: series, episodes and what became of each download.

Typical use::

    conn = open_database(root.database)
    with transaction(conn):
        series = upsert_series(conn, site="animeheaven", url=url, title=title, now=utc_now())
        sync_episodes(conn, series.id, [(e.number, e.ref) for e in listed], utc_now())
"""

from tsuzuki.storage.database import connect, open_database, prepare_database, transaction
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
from tsuzuki.storage.files import (
    confirm_delivery,
    confirm_visitor_delivery,
    remove_file,
    sweep_expired,
)
from tsuzuki.storage.library import (
    add_to_library,
    get_summary,
    in_library,
    library_size,
    list_summaries,
)
from tsuzuki.storage.records import (
    EpisodeRecord,
    EpisodeStatus,
    RequestRecord,
    SeriesRecord,
    SeriesSummary,
    view_status,
)
from tsuzuki.storage.retention import RetentionPolicy, expiry_for, has_room
from tsuzuki.storage.series import (
    delete_series,
    get_series,
    get_series_by_url,
    list_series,
    upsert_series,
)
from tsuzuki.storage.times import utc_now
from tsuzuki.storage.visitors import create_visitor, find_visitor, touch_visitor
from tsuzuki.storage.wants import (
    QueueRow,
    cancel_request,
    get_request,
    open_count,
    open_rows,
    request_episode,
    requests_for_series,
)
from tsuzuki.storage.work import abandon, claim_next, recover_interrupted

__all__ = [
    "EpisodeRecord",
    "EpisodeStatus",
    "QueueRow",
    "RequestRecord",
    "RetentionPolicy",
    "SeriesRecord",
    "SeriesSummary",
    "abandon",
    "add_to_library",
    "cancel_request",
    "claim_next",
    "confirm_delivery",
    "confirm_visitor_delivery",
    "connect",
    "count_by_status",
    "create_visitor",
    "delete_series",
    "due_for_expiry",
    "expiry_for",
    "find_episode",
    "find_visitor",
    "get_episode",
    "get_request",
    "get_series",
    "get_series_by_url",
    "get_summary",
    "has_room",
    "in_library",
    "library_size",
    "list_by_status",
    "list_episodes",
    "list_series",
    "list_summaries",
    "open_count",
    "open_database",
    "open_rows",
    "prepare_database",
    "ready_bytes",
    "recover_interrupted",
    "remove_file",
    "request_episode",
    "requests_for_series",
    "sweep_expired",
    "sync_episodes",
    "touch_visitor",
    "upsert_series",
    "transaction",
    "utc_now",
    "view_status",
]
