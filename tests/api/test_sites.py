from fastapi.testclient import TestClient


def test_lists_the_built_in_sites(client: TestClient) -> None:
    sites = client.get("/api/sites").json()
    assert {"host": "animeheaven.me", "how": "Built-in adapter", "state": "working"} in sites


def test_testing_a_built_in_site_says_it_works(client: TestClient) -> None:
    body = client.post("/api/sites/test", json={"url": "https://animeheaven.me/anime.php?x"}).json()
    assert body["host"] == "animeheaven.me"
    assert body["steps"][0]["outcome"] == "worked"
    assert body["profilePath"] is None


def test_testing_an_unknown_site_is_honest_that_the_rest_is_not_built(
    client: TestClient,
) -> None:
    body = client.post("/api/sites/test", json={"url": "https://new-site.example/series"}).json()
    assert body["host"] == "new-site.example"
    assert [s["outcome"] for s in body["steps"]] == ["missing", "missing", "missing", "skipped"]


def test_testing_something_that_is_not_a_url_is_rejected(client: TestClient) -> None:
    response = client.post("/api/sites/test", json={"url": "not a url"})
    assert response.status_code == 422


def test_saving_a_profile_is_not_supported_yet(client: TestClient) -> None:
    response = client.post("/api/sites/profiles", json={"url": "https://new-site.example/s"})
    assert response.status_code == 501
