import pytest
from fastapi.testclient import TestClient

from tsuzuki.api.app import status_for
from tsuzuki.core.errors import (
    ConfigError,
    DownloadError,
    FetchError,
    InvalidTransitionError,
    SiteNotSupportedError,
    StorageError,
    TsuzukiError,
)


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (InvalidTransitionError("x"), 409),
        (StorageError("x"), 500),
        (ConfigError("x"), 422),
        (SiteNotSupportedError("x"), 422),
        (FetchError("x", retryable=True), 502),
        (DownloadError("x"), 502),
        (TsuzukiError("x"), 400),
    ],
)
def test_each_error_becomes_the_right_status(error: TsuzukiError, status: int) -> None:
    assert status_for(error) == status


def test_adding_a_site_nobody_supports_explains_what_is_supported() -> None:
    import tempfile
    from pathlib import Path

    from tsuzuki.api import ApiState, create_app
    from tsuzuki.core.root import Root

    with tempfile.TemporaryDirectory() as folder:
        state = ApiState(root=Root(Path(folder), "test"))
        with TestClient(create_app(state, sweep=False)) as client:
            response = client.post("/api/series", json={"url": "https://unknown.example/a"})
    assert response.status_code == 422
    assert "Supported:" in response.json()["detail"]
