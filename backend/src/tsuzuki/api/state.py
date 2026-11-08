"""What the routes share: where things live, the settings, and how to open the database."""

import sqlite3
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

from tsuzuki.api.progress import ProgressBoard
from tsuzuki.core.root import Root
from tsuzuki.sites.base import Site
from tsuzuki.sites.registry import site_for
from tsuzuki.storage import RetentionPolicy, connect, prepare_database, utc_now

DEFAULT_SLOTS = 3


@dataclass
class ApiState:
    root: Root
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)
    slots: int = DEFAULT_SLOTS
    progress: ProgressBoard = field(default_factory=ProgressBoard)
    # Both are replaceable so tests can run without the network or the real clock.
    resolve_site: Callable[[str], Site] = site_for
    clock: Callable[[], datetime] = utc_now

    def prepare(self) -> None:
        """Create the database or bring it up to date. Run once, before serving requests."""
        prepare_database(self.root.database)

    @contextmanager
    def database(self) -> Generator[sqlite3.Connection]:
        """A connection for one request. SQLite connections belong to one thread, and each
        request may run on a different one, so none is kept between requests."""
        conn = connect(self.root.database)
        try:
            yield conn
        finally:
            conn.close()
