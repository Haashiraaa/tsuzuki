"""Pure HTML -> data functions for AnimeHeaven pages: no network, no logging.

All selectors live at the top so a layout change is a one-place fix.
"""

from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from tsuzuki.core.errors import ParseError
from tsuzuki.core.models import Episode

TITLE_META = 'meta[property="og:title"]'
TITLE_FALLBACK = "title"
EPISODE_LINKS = "a[href='gate.php'][id]"
EPISODE_NUMBER = "div.watch2"
VIDEO_SOURCES = ("video source[src]", "video[src]")


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def attr(tag: Tag, name: str) -> str | None:
    """An attribute as a plain string (bs4 may give a list for multi-valued ones)."""
    value = tag.get(name)
    if value is None:
        return None
    return value if isinstance(value, str) else " ".join(value)


def parse_title(soup: BeautifulSoup) -> str:
    title = meta_title(soup) or page_title(soup)
    if not title:
        raise ParseError("Series title not found (no og:title or <title>)")
    return title


def meta_title(soup: BeautifulSoup) -> str:
    tag = soup.select_one(TITLE_META)
    return (attr(tag, "content") or "").strip() if tag else ""


def page_title(soup: BeautifulSoup) -> str:
    tag = soup.select_one(TITLE_FALLBACK)
    return tag.get_text(strip=True) if tag else ""


def parse_episodes(soup: BeautifulSoup) -> tuple[Episode, ...]:
    episodes = tuple(parse_episode(tag) for tag in soup.select(EPISODE_LINKS))
    if not episodes:
        raise ParseError("No episodes found on the series page")
    return episodes


def parse_episode(tag: Tag) -> Episode:
    ref = (attr(tag, "id") or "").strip()
    number_tag = tag.select_one(EPISODE_NUMBER)
    number = number_tag.get_text(strip=True) if number_tag else ""
    if not ref or not number:
        raise ParseError(f"Episode link is missing its id or number: {tag}")
    return Episode(number=number, ref=ref)


def parse_video_url(soup: BeautifulSoup, page_url: str) -> str:
    """The video's absolute URL, resolved against the page it was found on."""
    for selector in VIDEO_SOURCES:
        tag = soup.select_one(selector)
        src = attr(tag, "src") if tag else None
        if src:
            return urljoin(page_url, src)
    raise ParseError("No video source found on the episode page")
