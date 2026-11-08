"""Visitors: anonymous browsers, each with a private library and request list.

A visitor is a random secret token kept in the browser's cookie. Only its hash is stored, so a
copy of the database cannot be used to act as anyone. There are no names, emails or passwords:
whoever holds the token is that visitor, which is also what makes a "restore my library" link
possible.
"""

import hashlib
import secrets
import sqlite3
from datetime import datetime

from tsuzuki.storage.times import to_text


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_visitor(conn: sqlite3.Connection, now: datetime) -> tuple[int, str]:
    """A new visitor. Returns their id and the secret token to give their browser."""
    token = new_token()
    stamp = to_text(now)
    cursor = conn.execute(
        "INSERT INTO visitors (token_hash, created_at, last_seen_at) VALUES (?, ?, ?)",
        (hash_token(token), stamp, stamp),
    )
    if cursor.lastrowid is None:
        raise RuntimeError("SQLite did not report the new visitor's id")
    return cursor.lastrowid, token


def find_visitor(conn: sqlite3.Connection, token: str) -> int | None:
    row = conn.execute(
        "SELECT id FROM visitors WHERE token_hash = ?", (hash_token(token),)
    ).fetchone()
    return int(row["id"]) if row else None


def touch_visitor(conn: sqlite3.Connection, visitor_id: int, now: datetime) -> None:
    conn.execute("UPDATE visitors SET last_seen_at = ? WHERE id = ?", (to_text(now), visitor_id))
