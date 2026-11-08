from datetime import datetime, timedelta
from pathlib import Path
from sqlite3 import Connection

from fastapi.testclient import TestClient

from tests._helpers import make_episodes, make_ready, make_series
from tsuzuki.api import ApiState
from tsuzuki.api.app import sweep_once
from tsuzuki.api.routes.files import send_then_deliver
from tsuzuki.storage import EpisodeStatus, get_episode, lifecycle


def ready_episode(
    conn: Connection, state: ApiState, now: datetime, content: bytes = b"video-bytes"
) -> tuple[int, Path]:
    series = make_series(conn, now)
    make_episodes(conn, series.id, now)
    record, path = make_ready(conn, state.root.downloads, series.id, "1", now, content=content)
    return record.id, path


def test_saving_sends_the_whole_file_then_removes_the_servers_copy(
    client: TestClient, api_conn: Connection, state: ApiState, now: datetime
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, b"x" * 5000)
    response = client.get(f"/api/episodes/{episode_id}/file")
    assert response.status_code == 200
    assert response.content == b"x" * 5000
    assert response.headers["content-length"] == "5000"
    assert 'filename="episode_1.mp4"' in response.headers["content-disposition"]
    record = get_episode(api_conn, episode_id)
    assert record is not None
    assert record.status is EpisodeStatus.DELIVERED
    assert not path.exists()


def test_the_row_is_kept_after_delivery_so_the_library_remembers(
    client: TestClient, api_conn: Connection, state: ApiState, now: datetime
) -> None:
    episode_id, _path = ready_episode(api_conn, state, now)
    client.get(f"/api/episodes/{episode_id}/file")
    series = client.get("/api/series").json()[0]
    assert series["downloaded"] == 1


def test_a_second_save_after_delivery_is_refused(
    client: TestClient, api_conn: Connection, state: ApiState, now: datetime
) -> None:
    episode_id, _path = ready_episode(api_conn, state, now)
    client.get(f"/api/episodes/{episode_id}/file")
    assert client.get(f"/api/episodes/{episode_id}/file").status_code == 409


def test_streaming_plays_the_file_and_keeps_it(
    client: TestClient, api_conn: Connection, state: ApiState, now: datetime
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, b"0123456789")
    response = client.get(f"/api/episodes/{episode_id}/stream")
    assert response.status_code == 200
    assert response.content == b"0123456789"
    assert path.exists()
    record = get_episode(api_conn, episode_id)
    assert record is not None
    assert record.status is EpisodeStatus.READY


def test_streaming_supports_seeking(
    client: TestClient, api_conn: Connection, state: ApiState, now: datetime
) -> None:
    episode_id, _path = ready_episode(api_conn, state, now, b"0123456789")
    response = client.get(f"/api/episodes/{episode_id}/stream", headers={"Range": "bytes=2-5"})
    assert response.status_code == 206
    assert response.content == b"2345"


def test_an_episode_that_is_not_ready_cannot_be_fetched(
    client: TestClient, api_conn: Connection, now: datetime
) -> None:
    series = make_series(api_conn, now)
    episode = make_episodes(api_conn, series.id, now)[0]
    assert client.get(f"/api/episodes/{episode.id}/file").status_code == 409
    assert client.get(f"/api/episodes/{episode.id}/stream").status_code == 409


def test_unknown_episode_file_is_404(client: TestClient) -> None:
    assert client.get("/api/episodes/999/file").status_code == 404


def test_a_missing_file_says_to_queue_it_again(
    client: TestClient, api_conn: Connection, state: ApiState, now: datetime
) -> None:
    episode_id, path = ready_episode(api_conn, state, now)
    path.unlink()
    response = client.get(f"/api/episodes/{episode_id}/file")
    assert response.status_code == 410
    assert "Queue it again" in response.json()["detail"]


def test_a_file_outside_the_downloads_folder_is_never_served(
    client: TestClient, api_conn: Connection, state: ApiState, now: datetime, tmp_path: Path
) -> None:
    episode_id, path = ready_episode(api_conn, state, now)
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    api_conn.execute("UPDATE episodes SET file_path = ? WHERE id = ?", (str(outside), episode_id))
    assert client.get(f"/api/episodes/{episode_id}/file").status_code == 404
    assert client.get(f"/api/episodes/{episode_id}/stream").status_code == 404
    assert outside.exists()
    assert path.exists()


def test_uncollected_files_are_removed_after_their_time(
    api_conn: Connection, state: ApiState, now: datetime
) -> None:
    episode_id, path = ready_episode(api_conn, state, now)
    later = now + timedelta(hours=25)
    state.clock = lambda: later
    assert sweep_once(state) == 1
    record = get_episode(api_conn, episode_id)
    assert record is not None
    assert record.status is EpisodeStatus.EXPIRED
    assert not path.exists()


def test_queueing_a_delivered_episode_again_fetches_it_from_the_site(
    client: TestClient, api_conn: Connection, state: ApiState, now: datetime
) -> None:
    episode_id, _path = ready_episode(api_conn, state, now)
    client.get(f"/api/episodes/{episode_id}/file")
    assert client.post(f"/api/episodes/{episode_id}/retry").status_code == 204
    record = get_episode(api_conn, episode_id)
    assert record is not None
    assert record.status is EpisodeStatus.QUEUED
    assert lifecycle.can_move(record.status, EpisodeStatus.DOWNLOADING)


def test_a_browser_that_gives_up_half_way_does_not_cost_the_file(
    api_conn: Connection, state: ApiState, now: datetime
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, b"x" * 3_000_000)
    stream = send_then_deliver(state, episode_id, path)
    next(stream)  # the first chunk goes out, then the connection drops
    stream.close()
    record = get_episode(api_conn, episode_id)
    assert record is not None
    assert record.status is EpisodeStatus.READY
    assert path.exists()
