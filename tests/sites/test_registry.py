import pytest

from tsuzuki.core.errors import ConfigError, SiteNotSupportedError
from tsuzuki.sites.registry import host_matches, site_for, supported_hosts


def test_known_host_gets_its_adapter() -> None:
    assert site_for("https://animeheaven.me/anime.php?abc").name == "AnimeHeaven"


def test_a_subdomain_of_a_known_host_matches() -> None:
    assert site_for("https://www.animeheaven.me/anime.php?abc").name == "AnimeHeaven"


def test_unknown_host_lists_what_is_supported() -> None:
    with pytest.raises(SiteNotSupportedError, match="animeheaven.me"):
        site_for("https://other-site.example/series")


def test_a_bad_url_is_a_config_error() -> None:
    with pytest.raises(ConfigError):
        site_for("not a url")


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("animeheaven.me", True),
        ("www.animeheaven.me", True),
        ("evilanimeheaven.me", False),
        ("animeheaven.me.evil.example", False),
    ],
)
def test_host_matching_is_not_fooled_by_lookalikes(host: str, expected: bool) -> None:
    assert host_matches(host, ("animeheaven.me",)) is expected


def test_supported_hosts_lists_the_registered_ones() -> None:
    assert "animeheaven.me" in supported_hosts()
