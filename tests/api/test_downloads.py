from datetime import datetime
from sqlite3 import Connection

from fastapi.testclient import TestClient

from tests._helpers import make_library, make_ready
from tests.api.conftest import Me
from tsuzuki.api import ApiState
from tsuzuki.storage import (
    EpisodeStatus,
    add_to_library,
    find_episode,
    get_episode,
    get_request,
    lifecycle,
    request_episode,
)

S = EpisodeStatus


def status_of(conn: Connection, episode_id: int) -> EpisodeStatus:
    record = get_episode(conn, episode_id)
    assert record is not None
    return record.status


def test_asking_for_episodes_queues_them(
    client: TestClient, api_conn: Connection, me: Me, now: datetime
) -> None:
    series, episodes = make_library(api_conn, me.id, now)
    response = client.post(
        "/api/downloads",
        json={"seriesId": series.id, "episodeIds": [episodes[0].id, episodes[1].id]},
    )
    assert response.status_code == 204
    assert status_of(api_conn, episodes[0].id) is S.QUEUED
    assert status_of(api_conn, episodes[2].id) is S.AVAILABLE


def test_asking_twice_is_harmless(
    client: TestClient, api_conn: Connection, me: Me, now: datetime
) -> None:
    series, episodes = make_library(api_conn, me.id, now)
    body = {"seriesId": series.id, "episodeIds": [episodes[0].id]}
    assert client.post("/api/downloads", json=body).status_code == 204
    assert client.post("/api/downloads", json=body).status_code == 204
    assert status_of(api_conn, episodes[0].id) is S.QUEUED


def test_a_series_that_is_not_in_my_library_is_refused(
    client: TestClient, api_conn: Connection, me: Me, friend_me: Me, now: datetime
) -> None:
    series, episodes = make_library(api_conn, friend_me.id, now)
    response = client.post(
        "/api/downloads", json={"seriesId": series.id, "episodeIds": [episodes[0].id]}
    )
    assert response.status_code == 404
    assert status_of(api_conn, episodes[0].id) is S.AVAILABLE


def test_an_episode_from_another_series_is_refused_and_nothing_is_queued(
    client: TestClient, api_conn: Connection, me: Me, now: datetime
) -> None:
    first, mine = make_library(api_conn, me.id, now)
    _other, theirs = make_library(
        api_conn, me.id, now, url="https://animeheaven.me/anime.php?other", title="Other"
    )
    response = client.post(
        "/api/downloads", json={"seriesId": first.id, "episodeIds": [mine[0].id, theirs[0].id]}
    )
    assert response.status_code == 404
    assert status_of(api_conn, mine[0].id) is S.AVAILABLE


def test_queue_lists_waiting_active_failed_and_finished(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    series, _ = make_library(api_conn, me.id, now, numbers=("1", "2", "3", "4"))
    one, two, three, four = (find_episode(api_conn, series.id, n) for n in "1234")
    assert one and two and three and four
    for episode in (one, two, three, four):
        request_episode(api_conn, me.id, episode.id, now, state.retention)
    lifecycle.start(api_conn, three.id, now)
    lifecycle.start(api_conn, four.id, now)
    lifecycle.fail(api_conn, four.id, now, "timed out after 5 attempts")
    lifecycle.start(api_conn, one.id, now)
    path = state.root.downloads / "Sample-Show" / "episode_1.mp4"
    path.parent.mkdir()
    path.write_bytes(b"x")
    lifecycle.finish(api_conn, one.id, now, file_path=str(path), size_bytes=1, expires_at=now)
    state.progress.update(three.id, done=0, total=1000, method="aria2 · 8 connections")
    state.progress.update(three.id, done=250, total=1000)

    body = client.get("/api/queue").json()

    assert body["slots"] == 3
    assert [a["name"] for a in body["active"]] == ["Sample Show · Episode 3"]
    assert body["active"][0]["method"] == "aria2 · 8 connections"
    assert body["active"][0]["percent"] == 25
    waiting = {w["name"]: w for w in body["waiting"]}
    assert waiting["Sample Show · Episode 2"]["note"] == "Waiting for a free slot"
    assert waiting["Sample Show · Episode 2"]["failed"] is False
    assert waiting["Sample Show · Episode 4"]["failed"] is True
    note = waiting["Sample Show · Episode 4"]["note"]
    assert note == "Failed: timed out after 5 attempts. Safe to retry."
    assert [f["name"] for f in body["finished"]] == ["Sample Show · Episode 1"]
    assert body["exampleFile"] == "Downloads/Sample-Show/episode_1.mp4"


def test_the_queue_never_shows_the_servers_folder_path(
    client: TestClient, me: Me, state: ApiState
) -> None:
    body = client.get("/api/queue").json()
    assert body["downloadsFolder"] == "Downloads"
    assert str(state.root.path) not in str(body)


def test_active_download_without_progress_yet_says_starting(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    _series, episodes = make_library(api_conn, me.id, now)
    request_episode(api_conn, me.id, episodes[0].id, now, state.retention)
    lifecycle.start(api_conn, episodes[0].id, now)
    active = client.get("/api/queue").json()["active"][0]
    assert active["method"] == "Starting"
    assert active["percent"] == 0
    assert active["etaSeconds"] is None


def test_retry_puts_a_failed_episode_back_in_the_queue(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    _series, episodes = make_library(api_conn, me.id, now)
    request_episode(api_conn, me.id, episodes[0].id, now, state.retention)
    lifecycle.start(api_conn, episodes[0].id, now)
    lifecycle.fail(api_conn, episodes[0].id, now, "boom")
    assert client.post(f"/api/episodes/{episodes[0].id}/retry").status_code == 204
    assert status_of(api_conn, episodes[0].id) is S.QUEUED


def test_retry_on_a_running_episode_is_a_conflict(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    _series, episodes = make_library(api_conn, me.id, now)
    request_episode(api_conn, me.id, episodes[0].id, now, state.retention)
    lifecycle.start(api_conn, episodes[0].id, now)
    assert client.post(f"/api/episodes/{episodes[0].id}/retry").status_code == 409


def test_cancel_takes_a_waiting_episode_out_of_the_queue(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    _series, episodes = make_library(api_conn, me.id, now)
    request_episode(api_conn, me.id, episodes[0].id, now, state.retention)
    assert client.post(f"/api/episodes/{episodes[0].id}/cancel").status_code == 204
    assert status_of(api_conn, episodes[0].id) is S.AVAILABLE
    assert get_request(api_conn, me.id, episodes[0].id) is None


def test_cancel_on_a_running_episode_asks_the_worker_to_stop(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    _series, episodes = make_library(api_conn, me.id, now)
    request_episode(api_conn, me.id, episodes[0].id, now, state.retention)
    lifecycle.start(api_conn, episodes[0].id, now)
    assert client.post(f"/api/episodes/{episodes[0].id}/cancel").status_code == 204
    assert state.progress.cancel_requested(episodes[0].id)
    assert status_of(api_conn, episodes[0].id) is S.DOWNLOADING


def test_cancelling_never_stops_a_download_someone_else_is_waiting_for(
    client: TestClient,
    api_conn: Connection,
    state: ApiState,
    me: Me,
    friend_me: Me,
    now: datetime,
) -> None:
    series, episodes = make_library(api_conn, me.id, now)
    add_to_library(api_conn, friend_me.id, series.id, now)
    request_episode(api_conn, me.id, episodes[0].id, now, state.retention)
    request_episode(api_conn, friend_me.id, episodes[0].id, now, state.retention)
    lifecycle.start(api_conn, episodes[0].id, now)
    assert client.post(f"/api/episodes/{episodes[0].id}/cancel").status_code == 204
    assert not state.progress.cancel_requested(episodes[0].id)
    assert get_request(api_conn, friend_me.id, episodes[0].id) is not None


def test_cancel_on_an_episode_i_never_asked_for_is_a_conflict(
    client: TestClient, api_conn: Connection, me: Me, now: datetime
) -> None:
    _series, episodes = make_library(api_conn, me.id, now)
    assert client.post(f"/api/episodes/{episodes[0].id}/cancel").status_code == 409


def test_unknown_episode_is_404(client: TestClient, me: Me) -> None:
    assert client.post("/api/episodes/999/retry").status_code == 404
    assert client.post("/api/episodes/999/cancel").status_code == 404


def test_pause_is_not_supported_yet(client: TestClient) -> None:
    response = client.post("/api/episodes/1/pause")
    assert response.status_code == 501
    assert "not supported" in response.json()["detail"]


def test_a_ready_episode_can_be_withdrawn_without_deleting_it_for_others(
    client: TestClient,
    api_conn: Connection,
    state: ApiState,
    me: Me,
    friend_me: Me,
    now: datetime,
) -> None:
    series, episodes = make_library(api_conn, me.id, now)
    add_to_library(api_conn, friend_me.id, series.id, now)
    request_episode(api_conn, me.id, episodes[0].id, now, state.retention)
    request_episode(api_conn, friend_me.id, episodes[0].id, now, state.retention)
    lifecycle.start(api_conn, episodes[0].id, now)
    path = state.root.downloads / "x.mp4"
    path.write_bytes(b"x")
    lifecycle.finish(
        api_conn, episodes[0].id, now, file_path=str(path), size_bytes=1, expires_at=now
    )
    assert client.post(f"/api/episodes/{episodes[0].id}/cancel").status_code == 204
    assert path.exists()
    assert status_of(api_conn, episodes[0].id) is S.READY


def test_helpers_still_build_ready_files(
    api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    series, _ = make_library(api_conn, me.id, now)
    record, path = make_ready(api_conn, state.root.downloads, series.id, "1", now)
    assert path.exists()
    assert record.status is S.READY
