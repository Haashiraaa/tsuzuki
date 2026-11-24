from pathlib import Path

import pytest

from tsuzuki.core.errors import ConfigError, ParseError
from tsuzuki.core.models import DownloadJob, MediaSource, Selection


class TestMediaSource:
    @pytest.mark.parametrize("url", ["http://cdn.example/v.mp4", "https://cdn.example/v.mp4"])
    def test_web_urls_are_accepted(self, url: str) -> None:
        assert MediaSource(url).url == url

    @pytest.mark.parametrize("url", ["ftp://x/v.mp4", "file:///etc/passwd", "javascript:1", ""])
    def test_other_schemes_are_refused(self, url: str) -> None:
        with pytest.raises(ParseError):
            MediaSource(url)


class TestSelection:
    def test_defaults(self) -> None:
        selection = Selection()
        assert (selection.episode, selection.limit, selection.newest_first) == (None, None, True)

    @pytest.mark.parametrize("value", [0, -1])
    def test_episode_must_be_one_or_more(self, value: int) -> None:
        with pytest.raises(ConfigError):
            Selection(episode=value)

    @pytest.mark.parametrize("value", [0, -1])
    def test_limit_must_be_one_or_more(self, value: int) -> None:
        with pytest.raises(ConfigError):
            Selection(limit=value)

    def test_episode_and_limit_cannot_be_combined(self) -> None:
        with pytest.raises(ConfigError, match="together"):
            Selection(episode=1, limit=2)


def test_download_job_path() -> None:
    job = DownloadJob(MediaSource("https://x.example/v.mp4"), Path("/d/Show"), "episode_1.mp4")
    assert job.path == Path("/d/Show/episode_1.mp4")
