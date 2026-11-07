-- Series the user added, and every episode Tsuzuki has seen on the site.
-- A downloaded file may be deleted from disk (after delivery or expiry); its row stays.

CREATE TABLE series (
    id         INTEGER PRIMARY KEY,
    site       TEXT    NOT NULL,
    url        TEXT    NOT NULL UNIQUE,
    title      TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);

CREATE TABLE episodes (
    id         INTEGER PRIMARY KEY,
    series_id  INTEGER NOT NULL REFERENCES series(id) ON DELETE CASCADE,
    number     TEXT    NOT NULL,
    ordinal    REAL    NOT NULL,
    ref        TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'available'
               CHECK (status IN ('available', 'queued', 'downloading', 'ready',
                                 'delivered', 'expired', 'failed')),
    file_path  TEXT,
    size_bytes INTEGER,
    error      TEXT,
    attempts   INTEGER NOT NULL DEFAULT 0,
    expires_at TEXT,
    updated_at TEXT    NOT NULL,
    UNIQUE (series_id, number)
);

CREATE INDEX episodes_by_series ON episodes (series_id, ordinal);
CREATE INDEX episodes_by_status ON episodes (status);
CREATE INDEX episodes_by_expiry ON episodes (expires_at) WHERE status = 'ready';
