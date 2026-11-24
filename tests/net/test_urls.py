import pytest

from tsuzuki.core.errors import ConfigError
from tsuzuki.net.urls import hostname, origin


def test_origin_drops_path_and_query() -> None:
    assert origin("https://animeheaven.me/anime.php?abc") == "https://animeheaven.me/"


@pytest.mark.parametrize(
    ("url", "host"),
    [("https://AnimeHeaven.ME/x", "animeheaven.me"), ("http://a.b.example:8080/", "a.b.example")],
)
def test_hostname_is_lowercase(url: str, host: str) -> None:
    assert hostname(url) == host


@pytest.mark.parametrize("url", ["ftp://x.example/", "not a url", "https:///path", ""])
def test_hostname_refuses_non_web_urls(url: str) -> None:
    with pytest.raises(ConfigError):
        hostname(url)
