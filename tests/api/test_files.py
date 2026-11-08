from datetime import datetime, timedelta
from pathlib import Path
from sqlite3 import Connection

from fastapi.testclient import TestClient

from tests._helpers import make_library, make_ready
from tests.api.conftest import Me
from tsuzuki.api import ApiState
from tsuzuki.api.app import sweep_once
from tsuzuki.api.routes.files import send_then_deliver
from tsuzuki.storage import (
    EpisodeStatus,
    add_to_library,
    get_episode,
    get_request,
    lifecycle,
    request_episode,
)


def ready_episode(
    conn: Connection, state: ApiState, now: datetime, who: list[Me], content: bytes = b"video-bytes"
) -> tuple[int, Path]:
    """An episode every visitor in ``who`` asked for, downloaded and waiting on the server."""
    series, episodes = make_library(conn, who[0].id, now)
    for other in who[1:]:
        add_to_library(conn, other.id, series.id, now)
    for visitor in who:
        request_episode(conn, visitor.id, episodes[0].id, now, state.retention)
    lifecycle.start(conn, episodes[0].id, now)
    path = state.root.downloads / "Sample-Show" / "episode_1.mp4"
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(content)
    lifecycle.finish(
        conn,
        episodes[0].id,
        now,
        file_path=str(path),
        size_bytes=len(content),
        expires_at=now + state.retention.ttl,
    )
    return episodes[0].id, path


def status_of(conn: Connection, episode_id: int) -> EpisodeStatus:
    record = get_episode(conn, episode_id)
    assert record is not None
    return record.status


def test_saving_sends_the_whole_file_then_removes_the_servers_copy(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, [me], b"x" * 5000)
    response = client.get(f"/api/episodes/{episode_id}/file")
    assert response.status_code == 200
    assert response.content == b"x" * 5000
    assert response.headers["content-length"] == "5000"
    assert 'filename="episode_1.mp4"' in response.headers["content-disposition"]
    assert status_of(api_conn, episode_id) is EpisodeStatus.DELIVERED
    assert not path.exists()


def test_the_library_remembers_what_was_saved(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    episode_id, _path = ready_episode(api_conn, state, now, [me])
    client.get(f"/api/episodes/{episode_id}/file")
    assert client.get("/api/series").json()[0]["downloaded"] == 1


def test_a_second_save_after_delivery_is_refused(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    episode_id, _path = ready_episode(api_conn, state, now, [me])
    client.get(f"/api/episodes/{episode_id}/file")
    assert client.get(f"/api/episodes/{episode_id}/file").status_code == 404


def test_the_file_stays_until_every_visitor_who_asked_has_saved_it(
    client: TestClient,
    friend: TestClient,
    api_conn: Connection,
    state: ApiState,
    me: Me,
    friend_me: Me,
    now: datetime,
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, [me, friend_me], b"shared")
    assert client.get(f"/api/episodes/{episode_id}/file").content == b"shared"
    assert path.exists()  # my friend has not saved it yet
    assert friend.get(f"/api/episodes/{episode_id}/file").content == b"shared"
    assert not path.exists()
    assert status_of(api_conn, episode_id) is EpisodeStatus.DELIVERED


def test_saving_for_me_does_not_mark_it_saved_for_my_friend(
    client: TestClient,
    friend: TestClient,
    api_conn: Connection,
    state: ApiState,
    me: Me,
    friend_me: Me,
    now: datetime,
) -> None:
    episode_id, _path = ready_episode(api_conn, state, now, [me, friend_me])
    client.get(f"/api/episodes/{episode_id}/file")
    assert [f["name"] for f in friend.get("/api/queue").json()["finished"]] == [
        "Sample Show · Episode 1"
    ]
    assert client.get("/api/queue").json()["finished"] == []


def test_someone_who_did_not_ask_for_the_episode_cannot_take_it(
    client: TestClient,
    friend: TestClient,
    api_conn: Connection,
    state: ApiState,
    me: Me,
    friend_me: Me,
    now: datetime,
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, [me])
    assert friend.get(f"/api/episodes/{episode_id}/file").status_code == 404
    assert friend.get(f"/api/episodes/{episode_id}/stream").status_code == 404
    assert path.exists()


def test_a_browser_with_no_visitor_cannot_take_anything(
    app_client_without_cookie: TestClient,
    api_conn: Connection,
    state: ApiState,
    me: Me,
    now: datetime,
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, [me])
    assert app_client_without_cookie.get(f"/api/episodes/{episode_id}/file").status_code == 404
    assert path.exists()


def test_streaming_plays_the_file_and_keeps_it(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, [me], b"0123456789")
    response = client.get(f"/api/episodes/{episode_id}/stream")
    assert response.status_code == 200
    assert response.content == b"0123456789"
    assert path.exists()
    assert status_of(api_conn, episode_id) is EpisodeStatus.READY


def test_streaming_supports_seeking(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    episode_id, _path = ready_episode(api_conn, state, now, [me], b"0123456789")
    response = client.get(f"/api/episodes/{episode_id}/stream", headers={"Range": "bytes=2-5"})
    assert response.status_code == 206
    assert response.content == b"2345"


def test_an_episode_that_is_not_ready_cannot_be_fetched(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    _series, episodes = make_library(api_conn, me.id, now)
    request_episode(api_conn, me.id, episodes[0].id, now, state.retention)
    assert client.get(f"/api/episodes/{episodes[0].id}/file").status_code == 409
    assert client.get(f"/api/episodes/{episodes[0].id}/stream").status_code == 409


def test_unknown_episode_file_is_404(client: TestClient, me: Me) -> None:
    assert client.get("/api/episodes/999/file").status_code == 404


def test_a_missing_file_says_to_queue_it_again(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, [me])
    path.unlink()
    response = client.get(f"/api/episodes/{episode_id}/file")
    assert response.status_code == 410
    assert "Queue it again" in response.json()["detail"]


def test_a_file_outside_the_downloads_folder_is_never_served(
    client: TestClient,
    api_conn: Connection,
    state: ApiState,
    me: Me,
    now: datetime,
    tmp_path: Path,
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, [me])
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")
    api_conn.execute("UPDATE episodes SET file_path = ? WHERE id = ?", (str(outside), episode_id))
    assert client.get(f"/api/episodes/{episode_id}/file").status_code == 404
    assert client.get(f"/api/episodes/{episode_id}/stream").status_code == 404
    assert outside.exists()
    assert path.exists()


def test_uncollected_files_are_removed_after_their_time(
    api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, [me])
    later = now + timedelta(hours=25)
    state.clock = lambda: later
    assert sweep_once(state) == 1
    assert status_of(api_conn, episode_id) is EpisodeStatus.EXPIRED
    assert not path.exists()


def test_after_expiry_the_visitor_sees_it_and_can_queue_it_again(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    episode_id, _path = ready_episode(api_conn, state, now, [me])
    state.clock = lambda: now + timedelta(hours=25)
    sweep_once(state)
    waiting = client.get("/api/queue").json()["waiting"]
    assert waiting[0]["failed"] is True
    assert "Expired" in waiting[0]["note"]
    assert client.post(f"/api/episodes/{episode_id}/retry").status_code == 204
    assert status_of(api_conn, episode_id) is EpisodeStatus.QUEUED


def test_queueing_a_saved_episode_again_fetches_it_from_the_site(
    client: TestClient, api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    episode_id, _path = ready_episode(api_conn, state, now, [me])
    client.get(f"/api/episodes/{episode_id}/file")
    assert client.post(f"/api/episodes/{episode_id}/retry").status_code == 204
    assert status_of(api_conn, episode_id) is EpisodeStatus.QUEUED
    request = get_request(api_conn, me.id, episode_id)
    assert request is not None
    assert request.delivered_at is None


def test_a_browser_that_gives_up_half_way_does_not_cost_the_file(
    api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    episode_id, path = ready_episode(api_conn, state, now, [me], b"x" * 3_000_000)
    stream = send_then_deliver(state, me.id, episode_id, path)
    next(stream)  # the first chunk goes out, then the connection drops
    stream.close()
    assert status_of(api_conn, episode_id) is EpisodeStatus.READY
    assert path.exists()


def test_helper_files_exist_for_other_tests(
    api_conn: Connection, state: ApiState, me: Me, now: datetime
) -> None:
    series, _ = make_library(api_conn, me.id, now)
    _record, path = make_ready(api_conn, state.root.downloads, series.id, "1", now)
    assert path.exists()
