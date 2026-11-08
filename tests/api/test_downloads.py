from datetime import datetime
from pathlib import Path
from sqlite3 import Connection

from fastapi.testclient import TestClient

from tests._helpers import make_episodes, make_ready, make_series
from tsuzuki.api import ApiState
from tsuzuki.storage import EpisodeStatus, find_episode, get_episode, lifecycle


def status_of(conn: Connection, episode_id: int) -> EpisodeStatus:
    record = get_episode(conn, episode_id)
    assert record is not None
    return record.status


def test_asking_for_episodes_queues_them(
    client: TestClient, api_conn: Connection, now: datetime
) -> None:
    series = make_series(api_conn, now)
    episodes = make_episodes(api_conn, series.id, now)
    response = client.post(
        "/api/downloads",
        json={"seriesId": series.id, "episodeIds": [episodes[0].id, episodes[1].id]},
    )
    assert response.status_code == 204
    assert status_of(api_conn, episodes[0].id) is EpisodeStatus.QUEUED
    assert status_of(api_conn, episodes[2].id) is EpisodeStatus.AVAILABLE


def test_asking_twice_is_harmless(client: TestClient, api_conn: Connection, now: datetime) -> None:
    series = make_series(api_conn, now)
    episode = make_episodes(api_conn, series.id, now)[0]
    body = {"seriesId": series.id, "episodeIds": [episode.id]}
    assert client.post("/api/downloads", json=body).status_code == 204
    assert client.post("/api/downloads", json=body).status_code == 204
    assert status_of(api_conn, episode.id) is EpisodeStatus.QUEUED


def test_episode_from_another_series_is_refused_and_nothing_is_queued(
    client: TestClient, api_conn: Connection, now: datetime
) -> None:
    first = make_series(api_conn, now)
    other = make_series(api_conn, now, url="https://animeheaven.me/anime.php?other", title="Other")
    mine = make_episodes(api_conn, first.id, now)[0]
    theirs = make_episodes(api_conn, other.id, now)[0]
    response = client.post(
        "/api/downloads", json={"seriesId": first.id, "episodeIds": [mine.id, theirs.id]}
    )
    assert response.status_code == 404
    assert status_of(api_conn, mine.id) is EpisodeStatus.AVAILABLE


def test_queue_lists_waiting_active_failed_and_finished(
    client: TestClient, api_conn: Connection, state: ApiState, now: datetime
) -> None:
    series = make_series(api_conn, now)
    make_episodes(api_conn, series.id, now, ("1", "2", "3", "4"))
    one, two, three, four = (find_episode(api_conn, series.id, n) for n in "1234")
    assert one and two and three and four
    lifecycle.queue(api_conn, two.id, now)
    lifecycle.queue(api_conn, three.id, now)
    lifecycle.start(api_conn, three.id, now)
    lifecycle.queue(api_conn, four.id, now)
    lifecycle.start(api_conn, four.id, now)
    lifecycle.fail(api_conn, four.id, now, "timed out after 5 attempts")
    make_ready(api_conn, state.root.downloads, series.id, "1", now)
    state.progress.update(three.id, done=0, total=1000, method="aria2 · 8 connections")
    state.progress.update(three.id, done=250, total=1000)

    body = client.get("/api/queue").json()

    assert body["slots"] == 3
    assert [a["name"] for a in body["active"]] == ["Sample Show · Episode 3"]
    assert body["active"][0]["method"] == "aria2 · 8 connections"
    assert body["active"][0]["percent"] == 25
    waiting = {w["name"]: w for w in body["waiting"]}
    assert waiting["Sample Show · Episode 2"]["failed"] is False
    assert waiting["Sample Show · Episode 2"]["note"] == "Waiting for a free slot"
    assert waiting["Sample Show · Episode 4"]["failed"] is True
    assert (
        waiting["Sample Show · Episode 4"]["note"]
        == "Failed: timed out after 5 attempts. Safe to retry."
    )
    assert [f["name"] for f in body["finished"]] == ["Sample Show · Episode 1"]
    assert body["exampleFile"] == "Downloads/episode_1.mp4"
    assert body["downloadsFolder"] == str(state.root.downloads)


def test_active_download_without_progress_yet_says_starting(
    client: TestClient, api_conn: Connection, now: datetime
) -> None:
    series = make_series(api_conn, now)
    episode = make_episodes(api_conn, series.id, now)[0]
    lifecycle.queue(api_conn, episode.id, now)
    lifecycle.start(api_conn, episode.id, now)
    active = client.get("/api/queue").json()["active"][0]
    assert active["method"] == "Starting"
    assert active["percent"] == 0
    assert active["etaSeconds"] is None


def test_retry_puts_a_failed_episode_back_in_the_queue(
    client: TestClient, api_conn: Connection, now: datetime
) -> None:
    series = make_series(api_conn, now)
    episode = make_episodes(api_conn, series.id, now)[0]
    lifecycle.queue(api_conn, episode.id, now)
    lifecycle.start(api_conn, episode.id, now)
    lifecycle.fail(api_conn, episode.id, now, "boom")
    assert client.post(f"/api/episodes/{episode.id}/retry").status_code == 204
    assert status_of(api_conn, episode.id) is EpisodeStatus.QUEUED


def test_retry_on_a_running_episode_is_a_conflict(
    client: TestClient, api_conn: Connection, now: datetime
) -> None:
    series = make_series(api_conn, now)
    episode = make_episodes(api_conn, series.id, now)[0]
    lifecycle.queue(api_conn, episode.id, now)
    lifecycle.start(api_conn, episode.id, now)
    assert client.post(f"/api/episodes/{episode.id}/retry").status_code == 409


def test_cancel_takes_a_waiting_episode_out_of_the_queue(
    client: TestClient, api_conn: Connection, now: datetime
) -> None:
    series = make_series(api_conn, now)
    episode = make_episodes(api_conn, series.id, now)[0]
    lifecycle.queue(api_conn, episode.id, now)
    assert client.post(f"/api/episodes/{episode.id}/cancel").status_code == 204
    assert status_of(api_conn, episode.id) is EpisodeStatus.AVAILABLE


def test_cancel_on_a_running_episode_asks_the_worker_to_stop(
    client: TestClient, api_conn: Connection, state: ApiState, now: datetime
) -> None:
    series = make_series(api_conn, now)
    episode = make_episodes(api_conn, series.id, now)[0]
    lifecycle.queue(api_conn, episode.id, now)
    lifecycle.start(api_conn, episode.id, now)
    assert client.post(f"/api/episodes/{episode.id}/cancel").status_code == 204
    assert state.progress.cancel_requested(episode.id)
    assert status_of(api_conn, episode.id) is EpisodeStatus.DOWNLOADING


def test_cancel_on_a_finished_episode_is_a_conflict(
    client: TestClient, api_conn: Connection, state: ApiState, now: datetime
) -> None:
    series = make_series(api_conn, now)
    make_episodes(api_conn, series.id, now)
    record, _path = make_ready(api_conn, state.root.downloads, series.id, "1", now)
    assert client.post(f"/api/episodes/{record.id}/cancel").status_code == 409


def test_unknown_episode_is_404(client: TestClient) -> None:
    assert client.post("/api/episodes/999/retry").status_code == 404
    assert client.post("/api/episodes/999/cancel").status_code == 404


def test_pause_is_not_supported_yet(client: TestClient) -> None:
    response = client.post("/api/episodes/1/pause")
    assert response.status_code == 501
    assert "not supported" in response.json()["detail"]


def test_downloads_folder_fixture_is_where_files_go(state: ApiState) -> None:
    assert Path(state.root.downloads).is_dir()
