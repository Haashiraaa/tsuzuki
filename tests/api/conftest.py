"""A server wired to a temporary folder and a fake site, so no test touches the network."""

import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tsuzuki.api import ApiState, create_app
from tsuzuki.core.models import Episode, MediaSource, Series
from tsuzuki.core.root import Root
from tsuzuki.sites.base import Site
from tsuzuki.storage import open_database

SERIES_URL = "https://animeheaven.me/anime.php?abc12"


class FakeSite:
    name = "fakesite"

    def fetch_series(self, url: str) -> Series:
        episodes = tuple(Episode(str(n), f"ref-{n}") for n in range(15, 0, -1))
        return Series("Sample Show", url, episodes)

    def resolve_media(self, series: Series, episode: Episode) -> MediaSource:
        return MediaSource("https://example.test/video.mp4")


@pytest.fixture
def state(tmp_path: Path, now: datetime) -> ApiState:
    root = Root(tmp_path, "test")
    root.downloads.mkdir()

    def resolve(_url: str) -> Site:
        return FakeSite()

    return ApiState(root=root, clock=lambda: now, resolve_site=resolve)


@pytest.fixture
def client(state: ApiState) -> Iterator[TestClient]:
    with TestClient(create_app(state, sweep=False)) as test_client:
        yield test_client


@pytest.fixture
def api_conn(state: ApiState) -> Iterator[sqlite3.Connection]:
    """A second connection to the server's own database, to set up and check rows."""
    connection = open_database(state.root.database)
    yield connection
    connection.close()
