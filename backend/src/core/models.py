"""Plain data shared across the whole package."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from tsuzuki.core.errors import ConfigError, ParseError

ALLOWED_SCHEMES = ("http", "https")


@dataclass(frozen=True)
class Episode:
    """One episode as listed on a series page. ``ref`` is whatever the site needs to fetch it."""

    number: str
    ref: str


@dataclass(frozen=True)
class Series:
    """A series page: its title, where it came from, and its episodes in listed order."""

    title: str
    url: str
    episodes: tuple[Episode, ...]


@dataclass(frozen=True)
class MediaSource:
    """A direct media URL plus the headers needed to fetch it."""

    url: str
    headers: Mapping[str, str] = field(default_factory=dict[str, str])

    def __post_init__(self) -> None:
        if urlparse(self.url).scheme not in ALLOWED_SCHEMES:
            raise ParseError(f"Unsupported media URL: {self.url!r}")


@dataclass(frozen=True)
class DownloadJob:
    """Everything a downloader needs: what to fetch and where to put it."""

    source: MediaSource
    directory: Path
    filename: str

    @property
    def path(self) -> Path:
        return self.directory / self.filename


@dataclass(frozen=True)
class Selection:
    """Which episodes to download. ``episode`` and ``limit`` are mutually exclusive."""

    episode: int | None = None
    limit: int | None = None
    newest_first: bool = True

    def __post_init__(self) -> None:
        for name in ("episode", "limit"):
            value = getattr(self, name)
            if value is not None and value < 1:
                raise ConfigError(f"{name} must be 1 or greater, got {value}")
        if self.episode is not None and self.limit is not None:
            raise ConfigError("episode and limit cannot be used together")
