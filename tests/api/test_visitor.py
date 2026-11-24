"""Each browser gets its own library and queue, with no accounts."""

from datetime import datetime, timedelta
from sqlite3 import Connection

from fastapi.testclient import TestClient

from tests._helpers import make_library, make_series
from tests.api.conftest import SERIES_URL, Me
from tsuzuki.api import ApiState, Limits
from tsuzuki.api.visitor import COOKIE
from tsuzuki.storage import request_episode


def test_looking_around_creates_nobody(client: TestClient, api_conn: Connection) -> None:
    assert client.get("/api/series").json() == []
    assert client.get("/api/queue").json()["waiting"] == []
    assert client.get("/api/sites").status_code == 200
    assert api_conn.execute("SELECT COUNT(*) FROM visitors").fetchone()[0] == 0
    assert COOKIE not in client.cookies


def test_the_first_series_added_creates_a_visitor_and_sets_the_cookie(
    client: TestClient, api_conn: Connection
) -> None:
    response = client.post("/api/series", json={"url": SERIES_URL})
    assert response.status_code == 200
    assert api_conn.execute("SELECT COUNT(*) FROM visitors").fetchone()[0] == 1
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{COOKIE}=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie.replace("Lax", "lax")
    assert "Max-Age=31536000" in cookie
    assert "Secure" not in cookie  # plain http, as in these tests


def test_the_same_browser_stays_the_same_visitor(client: TestClient, api_conn: Connection) -> None:
    client.post("/api/series", json={"url": SERIES_URL})
    response = client.post("/api/series", json={"url": SERIES_URL})
    assert "set-cookie" not in response.headers
    assert api_conn.execute("SELECT COUNT(*) FROM visitors").fetchone()[0] == 1
    assert len(client.get("/api/series").json()) == 1


def test_two_browsers_have_separate_libraries(client: TestClient, friend: TestClient) -> None:
    client.post("/api/series", json={"url": SERIES_URL})
    assert len(client.get("/api/series").json()) == 1
    assert friend.get("/api/series").json() == []


def test_a_friend_cannot_open_my_series_page(
    client: TestClient, friend: TestClient, friend_me: Me
) -> None:
    mine = client.post("/api/series", json={"url": SERIES_URL}).json()
    assert friend.get(f"/api/series/{mine['id']}").status_code == 404


def test_queues_are_separate_but_the_download_is_shared(
    client: TestClient, friend: TestClient, api_conn: Connection, state: ApiState
) -> None:
    mine = client.post("/api/series", json={"url": SERIES_URL}).json()
    theirs = friend.post("/api/series", json={"url": SERIES_URL}).json()
    assert mine["id"] == theirs["id"]  # one shared series
    episode = client.get(f"/api/series/{mine['id']}").json()["episodes"][0]
    client.post("/api/downloads", json={"seriesId": mine["id"], "episodeIds": [episode["id"]]})

    assert len(client.get("/api/queue").json()["waiting"]) == 1
    assert friend.get("/api/queue").json()["waiting"] == []
    mine_now = client.get(f"/api/series/{mine['id']}").json()["episodes"][0]["status"]
    theirs_now = friend.get(f"/api/series/{mine['id']}").json()["episodes"][0]["status"]
    assert (mine_now, theirs_now) == ("queued", "available")

    friend.post("/api/downloads", json={"seriesId": mine["id"], "episodeIds": [episode["id"]]})
    assert (
        api_conn.execute("SELECT COUNT(*) FROM episodes WHERE status = 'queued'").fetchone()[0] == 1
    )
    assert len(friend.get("/api/queue").json()["waiting"]) == 1


def test_library_counts_are_only_about_me(
    client: TestClient, friend: TestClient, state: ApiState
) -> None:
    mine = client.post("/api/series", json={"url": SERIES_URL}).json()
    friend.post("/api/series", json={"url": SERIES_URL})
    episode = client.get(f"/api/series/{mine['id']}").json()["episodes"][0]
    client.post("/api/downloads", json={"seriesId": mine["id"], "episodeIds": [episode["id"]]})
    assert client.get("/api/series").json()[0]["inProgress"] == 1
    assert friend.get("/api/series").json()[0]["inProgress"] == 0


def test_a_series_added_a_moment_ago_is_reused_without_asking_the_site_again(
    client: TestClient, friend: TestClient, state: ApiState
) -> None:
    calls: list[str] = []
    original = state.resolve_site

    def counting(url: str):  # type: ignore[no-untyped-def]
        calls.append(url)
        return original(url)

    state.resolve_site = counting
    client.post("/api/series", json={"url": SERIES_URL})
    friend.post("/api/series", json={"url": SERIES_URL})
    assert len(calls) == 1


def test_an_old_series_is_read_again_to_pick_up_new_episodes(
    client: TestClient, friend: TestClient, state: ApiState, now: datetime
) -> None:
    calls: list[str] = []
    original = state.resolve_site

    def counting(url: str):  # type: ignore[no-untyped-def]
        calls.append(url)
        return original(url)

    state.resolve_site = counting
    client.post("/api/series", json={"url": SERIES_URL})
    state.clock = lambda: now + timedelta(hours=2)
    friend.post("/api/series", json={"url": SERIES_URL})
    assert len(calls) == 2


class TestRestoreLink:
    def test_there_is_nothing_to_restore_before_doing_anything(self, client: TestClient) -> None:
        assert client.get("/api/me").json() == {"restorePath": None}

    def test_a_visitor_gets_a_private_link_to_their_library(self, client: TestClient) -> None:
        client.post("/api/series", json={"url": SERIES_URL})
        path = client.get("/api/me").json()["restorePath"]
        assert path.startswith("/api/restore/")
        assert client.cookies[COOKIE] in path

    def test_opening_the_link_in_another_browser_brings_the_library_back(
        self, client: TestClient, friend: TestClient
    ) -> None:
        client.post("/api/series", json={"url": SERIES_URL})
        path = client.get("/api/me").json()["restorePath"]
        assert friend.get("/api/series").json() == []
        response = friend.get(path, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/"
        assert COOKIE in response.headers["set-cookie"]
        assert len(friend.get("/api/series").json()) == 1

    def test_a_made_up_link_does_nothing(self, friend: TestClient) -> None:
        response = friend.get("/api/restore/not-a-real-token", follow_redirects=False)
        assert response.status_code == 404
        assert "set-cookie" not in response.headers


class TestLimits:
    def test_too_many_episodes_at_once_queues_none_and_says_how_many_are_allowed(
        self, client: TestClient, api_conn: Connection, me: Me, state: ApiState, now: datetime
    ) -> None:
        state.limits = Limits(max_open=3)
        series, episodes = make_library(
            api_conn, me.id, now, numbers=tuple(str(n) for n in range(1, 6))
        )
        response = client.post(
            "/api/downloads",
            json={"seriesId": series.id, "episodeIds": [e.id for e in episodes]},
        )
        assert response.status_code == 429
        assert "up to 3" in response.json()["detail"]
        assert client.get("/api/queue").json()["waiting"] == []

    def test_what_is_already_waiting_counts_toward_the_limit(
        self, client: TestClient, api_conn: Connection, me: Me, state: ApiState, now: datetime
    ) -> None:
        state.limits = Limits(max_open=2)
        series, episodes = make_library(api_conn, me.id, now)
        request_episode(api_conn, me.id, episodes[0].id, now, state.retention)
        request_episode(api_conn, me.id, episodes[1].id, now, state.retention)
        response = client.post(
            "/api/downloads", json={"seriesId": series.id, "episodeIds": [episodes[2].id]}
        )
        assert response.status_code == 429
        assert "already have 2" in response.json()["detail"]

    def test_the_limit_is_per_visitor(
        self,
        client: TestClient,
        friend: TestClient,
        api_conn: Connection,
        me: Me,
        friend_me: Me,
        state: ApiState,
        now: datetime,
    ) -> None:
        state.limits = Limits(max_open=1)
        series, episodes = make_library(api_conn, me.id, now)
        from tsuzuki.storage import add_to_library

        add_to_library(api_conn, friend_me.id, series.id, now)
        for browser, episode in ((client, episodes[0]), (friend, episodes[1])):
            response = browser.post(
                "/api/downloads", json={"seriesId": series.id, "episodeIds": [episode.id]}
            )
            assert response.status_code == 204

    def test_saving_an_episode_frees_room(
        self, client: TestClient, api_conn: Connection, me: Me, state: ApiState, now: datetime
    ) -> None:
        state.limits = Limits(max_open=1)
        series, episodes = make_library(api_conn, me.id, now)
        first = {"seriesId": series.id, "episodeIds": [episodes[0].id]}
        second = {"seriesId": series.id, "episodeIds": [episodes[1].id]}
        assert client.post("/api/downloads", json=first).status_code == 204
        assert client.post("/api/downloads", json=second).status_code == 429
        client.post(f"/api/episodes/{episodes[0].id}/cancel")
        assert client.post("/api/downloads", json=second).status_code == 204

    def test_a_full_library_refuses_new_series_but_not_ones_already_in_it(
        self, client: TestClient, state: ApiState
    ) -> None:
        state.limits = Limits(max_series=1)
        assert client.post("/api/series", json={"url": SERIES_URL}).status_code == 200
        assert client.post("/api/series", json={"url": SERIES_URL}).status_code == 200
        other = client.post("/api/series", json={"url": SERIES_URL + "x"})
        assert other.status_code == 429
        assert "library is full" in other.json()["detail"]


def test_series_made_directly_are_still_private_until_added(
    client: TestClient, api_conn: Connection, me: Me, now: datetime
) -> None:
    make_series(api_conn, now)
    assert client.get("/api/series").json() == []
