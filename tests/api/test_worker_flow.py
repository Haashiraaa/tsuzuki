"""The whole trip with a real worker: add a series, ask for an episode, wait for it, save it to
the device, and see the server's copy gone."""

import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import SERIES_URL, FakeSite
from tests.worker.conftest import FakeDownloader
from tsuzuki.api import ApiState, create_app
from tsuzuki.core.root import Root
from tsuzuki.download.pipeline import Notice
from tsuzuki.download.plan import DownloadPlan
from tsuzuki.sites.base import Site


def wait_until(condition: Callable[[], bool], seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def live_client(tmp_path: Path) -> Iterator[TestClient]:
    root = Root(tmp_path, "test")
    root.downloads.mkdir()
    downloader = FakeDownloader(size=4000)

    def resolve(_url: str) -> Site:
        return FakeSite()

    def plan(_notice: Notice) -> DownloadPlan:
        return DownloadPlan(downloader, 1)

    state = ApiState(root=root, resolve_site=resolve, make_plan=plan, poll_seconds=0.05)
    with TestClient(create_app(state, sweep=False, work=True)) as client:
        yield client


def test_asking_for_an_episode_downloads_it_and_saving_it_removes_the_servers_copy(
    live_client: TestClient, tmp_path: Path
) -> None:
    series_id = live_client.post("/api/series", json={"url": SERIES_URL}).json()["id"]
    episodes = live_client.get(f"/api/series/{series_id}").json()["episodes"]
    wanted = episodes[0]
    live_client.post("/api/downloads", json={"seriesId": series_id, "episodeIds": [wanted["id"]]})

    assert wait_until(lambda: len(live_client.get("/api/queue").json()["finished"]) == 1)
    queue = live_client.get("/api/queue").json()
    assert queue["finished"][0]["name"] == f"Sample Show · Episode {wanted['number']}"

    saved = live_client.get(f"/api/episodes/{wanted['id']}/file")
    assert saved.status_code == 200
    assert len(saved.content) == 4000

    assert live_client.get("/api/queue").json()["finished"] == []
    assert list((tmp_path / "Downloads").rglob("*.mp4")) == []
    library = live_client.get("/api/series").json()[0]
    assert library["downloaded"] == 1


def test_a_failed_download_shows_up_and_can_be_retried(tmp_path: Path) -> None:
    root = Root(tmp_path, "test")
    root.downloads.mkdir()
    from tsuzuki.core.errors import TsuzukiError

    downloader = FakeDownloader(errors=[TsuzukiError("no space left")])
    state = ApiState(
        root=root,
        resolve_site=lambda _url: FakeSite(),
        make_plan=lambda _n: DownloadPlan(downloader, 1),
        poll_seconds=0.05,
    )
    with TestClient(create_app(state, sweep=False, work=True)) as client:
        series_id = client.post("/api/series", json={"url": SERIES_URL}).json()["id"]
        episode = client.get(f"/api/series/{series_id}").json()["episodes"][0]
        client.post("/api/downloads", json={"seriesId": series_id, "episodeIds": [episode["id"]]})

        def failed() -> bool:
            waiting = client.get("/api/queue").json()["waiting"]
            return bool(waiting) and waiting[0]["failed"]

        assert wait_until(failed)
        note = client.get("/api/queue").json()["waiting"][0]["note"]
        assert "no space left" in note

        client.post(f"/api/episodes/{episode['id']}/retry")
        assert wait_until(lambda: len(client.get("/api/queue").json()["finished"]) == 1)
