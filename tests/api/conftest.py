"""A server wired to a temporary folder and a fake site, so no test touches the network."""

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tsuzuki.api import ApiState, create_app
from tsuzuki.api.visitor import COOKIE
from tsuzuki.core.models import Episode, MediaSource, Series
from tsuzuki.core.root import Root
from tsuzuki.sites.base import Site
from tsuzuki.storage import create_visitor, open_database

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


@dataclass(frozen=True)
class Me:
    """A visitor who already exists in the database, and holds the matching cookie."""

    id: int
    token: str


@pytest.fixture
def app(state: ApiState) -> FastAPI:
    return create_app(state, sweep=False, work=False)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def app_client_without_cookie(app: FastAPI) -> Iterator[TestClient]:
    """A browser that has never visited: no cookie at all."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def friend(app: FastAPI) -> Iterator[TestClient]:
    """A second browser: its own cookies, so its own visitor."""
    with TestClient(app) as test_client:
        yield test_client


def sign_in(browser: TestClient, conn: sqlite3.Connection, now: datetime) -> Me:
    visitor_id, token = create_visitor(conn, now)
    browser.cookies.set(COOKIE, token)
    return Me(visitor_id, token)


@pytest.fixture
def me(client: TestClient, api_conn: sqlite3.Connection, now: datetime) -> Me:
    return sign_in(client, api_conn, now)


@pytest.fixture
def friend_me(friend: TestClient, api_conn: sqlite3.Connection, now: datetime) -> Me:
    return sign_in(friend, api_conn, now)


@pytest.fixture
def api_conn(state: ApiState) -> Iterator[sqlite3.Connection]:
    """A second connection to the server's own database, to set up and check rows."""
    connection = open_database(state.root.database)
    yield connection
    connection.close()
