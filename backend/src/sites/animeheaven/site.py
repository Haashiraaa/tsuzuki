"""AnimeHeaven adapter: fetches pages and hands them to the parsing functions."""

from urllib.parse import urljoin

from backend.src.core.models import Episode, MediaSource, Series
from backend.src.net.http import fetch_text
from backend.src.net.urls import origin
from backend.src.sites.animeheaven.parsing import (
    make_soup,
    parse_episodes,
    parse_title,
    parse_video_url,
)
from backend.src.sites.base import SiteEntry

GATE_PATH = "gate.php"
# the gate page only serves the video for the cookie holding the episode id
COOKIE_NAME = "key"


class AnimeHeavenSite:
    name = "AnimeHeaven"

    def fetch_series(self, url: str) -> Series:
        soup = make_soup(fetch_text(url, headers=page_headers(url)))
        return Series(title=parse_title(soup), url=url, episodes=parse_episodes(soup))

    def resolve_media(self, series: Series, episode: Episode) -> MediaSource:
        gate_url = urljoin(series.url, GATE_PATH)
        html = fetch_text(
            gate_url,
            headers=page_headers(series.url),
            cookies={COOKIE_NAME: episode.ref},
        )
        video_url = parse_video_url(make_soup(html), gate_url)
        return MediaSource(url=video_url, headers=page_headers(series.url))


def page_headers(url: str) -> dict[str, str]:
    """The site checks the Referer on both pages and video requests."""
    return {"Referer": origin(url)}


ENTRY = SiteEntry(name=AnimeHeavenSite.name, hosts=(
    "animeheaven.me",), create=AnimeHeavenSite)
