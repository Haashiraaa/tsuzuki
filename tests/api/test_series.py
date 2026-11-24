from datetime import datetime
from sqlite3 import Connection

from fastapi.testclient import TestClient

from tests._helpers import make_library
from tests.api.conftest import SERIES_URL, Me
from tsuzuki.storage import EpisodeStatus, find_episode, lifecycle


def test_library_starts_empty(client: TestClient) -> None:
    response = client.get("/api/series")
    assert response.status_code == 200
    assert response.json() == []


def test_add_series_saves_it_with_all_its_episodes(client: TestClient) -> None:
    response = client.post("/api/series", json={"url": SERIES_URL})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Sample Show"
    assert body["site"] == "fakesite"
    assert body["total"] == 15
    assert body["downloaded"] == 0
    assert body["inProgress"] == 0
    assert client.get("/api/series").json() == [body]


def test_adding_again_refreshes_instead_of_duplicating(client: TestClient) -> None:
    client.post("/api/series", json={"url": SERIES_URL})
    client.post("/api/series", json={"url": SERIES_URL})
    assert len(client.get("/api/series").json()) == 1


def test_adding_again_keeps_each_episodes_status(
    client: TestClient, api_conn: Connection, now: datetime
) -> None:
    series_id = client.post("/api/series", json={"url": SERIES_URL}).json()["id"]
    episode = find_episode(api_conn, series_id, "3")
    assert episode is not None
    lifecycle.queue(api_conn, episode.id, now)
    client.post("/api/series", json={"url": SERIES_URL})
    kept = find_episode(api_conn, series_id, "3")
    assert kept is not None
    assert kept.status is EpisodeStatus.QUEUED


def test_series_page_shows_one_page_newest_first(client: TestClient) -> None:
    series_id = client.post("/api/series", json={"url": SERIES_URL}).json()["id"]
    body = client.get(f"/api/series/{series_id}").json()
    assert body["listed"] == 15
    assert [e["number"] for e in body["episodes"]] == [str(n) for n in range(15, 3, -1)]
    assert body["episodes"][0]["status"] == "available"


def test_series_page_oldest_first_and_all(client: TestClient) -> None:
    series_id = client.post("/api/series", json={"url": SERIES_URL}).json()["id"]
    body = client.get(f"/api/series/{series_id}", params={"order": "oldest", "all": "true"}).json()
    assert [e["number"] for e in body["episodes"]] == [str(n) for n in range(1, 16)]


def test_series_page_explains_how_the_site_was_read(client: TestClient) -> None:
    series_id = client.post("/api/series", json={"url": SERIES_URL}).json()["id"]
    steps = client.get(f"/api/series/{series_id}").json()["steps"]
    assert [s["title"] for s in steps] == [
        "Saved profile",
        "Generic detection",
        "yt-dlp",
        "AI repair",
    ]
    assert steps[0]["outcome"] == "worked"


def test_unknown_series_is_404(client: TestClient) -> None:
    assert client.get("/api/series/999").status_code == 404


def test_bad_order_is_rejected(
    client: TestClient, api_conn: Connection, me: Me, now: datetime
) -> None:
    series, _ = make_library(api_conn, me.id, now)
    assert client.get(f"/api/series/{series.id}", params={"order": "sideways"}).status_code == 422
