"""Removing finished files from the server's disk, safely.

The database change is committed first, then the file is deleted. If the process dies in
between, the row says "delivered" and a stray file is left over, which wastes space but never
loses a download anyone is still waiting for.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

from tsuzuki.core.errors import StorageError
from tsuzuki.storage import lifecycle
from tsuzuki.storage.database import transaction
from tsuzuki.storage.episodes import due_for_expiry, get_episode
from tsuzuki.storage.records import EpisodeRecord, EpisodeStatus
from tsuzuki.storage.wants import mark_delivered


def remove_file(downloads_root: Path, file_path: str | None) -> bool:
    """Delete one file under ``downloads_root``. True if a file was removed, False if there was
    nothing to remove. Refuses anything outside the root."""
    if not file_path:
        return False
    target = Path(file_path).resolve()
    if not target.is_relative_to(downloads_root.resolve()):
        raise StorageError(f"Refusing to delete a file outside the downloads folder: {target}")
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True


def confirm_delivery(
    conn: sqlite3.Connection, downloads_root: Path, episode_id: int, now: datetime
) -> EpisodeRecord:
    """Call this once the whole file has reached the device, never before."""
    with transaction(conn):
        path = file_path_of(conn, episode_id)
        record = lifecycle.deliver(conn, episode_id, now)
    remove_file(downloads_root, path)
    return record


def confirm_visitor_delivery(
    conn: sqlite3.Connection,
    downloads_root: Path,
    visitor_id: int,
    episode_id: int,
    now: datetime,
) -> bool:
    """This visitor has the whole file. The server's copy goes only when the last visitor who
    asked for the episode has it; until then it stays for the others. Returns True if the file
    was removed."""
    path: str | None = None
    with transaction(conn):
        remaining = mark_delivered(conn, visitor_id, episode_id, now)
        episode = get_episode(conn, episode_id)
        if remaining == 0 and episode is not None and episode.status is EpisodeStatus.READY:
            path = episode.file_path
            lifecycle.deliver(conn, episode_id, now)
    return remove_file(downloads_root, path)


def sweep_expired(
    conn: sqlite3.Connection, downloads_root: Path, now: datetime
) -> list[EpisodeRecord]:
    """Remove every file nobody collected in time. Returns the episodes that expired."""
    expired: list[EpisodeRecord] = []
    for due in due_for_expiry(conn, now):
        with transaction(conn):
            record = lifecycle.expire(conn, due.id, now)
        remove_file(downloads_root, due.file_path)
        expired.append(record)
    return expired


def file_path_of(conn: sqlite3.Connection, episode_id: int) -> str | None:
    row = conn.execute("SELECT file_path FROM episodes WHERE id = ?", (episode_id,)).fetchone()
    return row["file_path"] if row else None
