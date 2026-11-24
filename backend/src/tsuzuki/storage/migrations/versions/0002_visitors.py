# pyright: basic
"""Visitors: each browser gets its own library and its own list of requested episodes.

Series, episodes and the files on disk stay shared, so two people asking for the same episode
cause one download. A visitor is an anonymous random token kept in a cookie (only its hash is
stored here); there are no accounts.

``library``   which series a visitor added.
``requests``  which episodes a visitor asked for, and when they saved each one.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

STATEMENTS = [
    """
    CREATE TABLE visitors (
        id           INTEGER PRIMARY KEY,
        token_hash   TEXT NOT NULL UNIQUE,
        created_at   TEXT NOT NULL,
        last_seen_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE library (
        visitor_id INTEGER NOT NULL REFERENCES visitors(id) ON DELETE CASCADE,
        series_id  INTEGER NOT NULL REFERENCES series(id)   ON DELETE CASCADE,
        added_at   TEXT    NOT NULL,
        PRIMARY KEY (visitor_id, series_id)
    )
    """,
    "CREATE INDEX library_by_series ON library (series_id)",
    """
    CREATE TABLE requests (
        id           INTEGER PRIMARY KEY,
        visitor_id   INTEGER NOT NULL REFERENCES visitors(id) ON DELETE CASCADE,
        episode_id   INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
        requested_at TEXT    NOT NULL,
        delivered_at TEXT,
        UNIQUE (visitor_id, episode_id)
    )
    """,
    "CREATE INDEX requests_by_episode ON requests (episode_id)",
]


def upgrade() -> None:
    for statement in STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TABLE requests")
    op.execute("DROP TABLE library")
    op.execute("DROP TABLE visitors")
