"""The contract every site adapter fulfils."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from tsuzuki.core.models import Episode, MediaSource, Series


class Site(Protocol):
    """Two jobs: list a series' episodes, and turn one episode into a downloadable source."""

    name: str

    def fetch_series(self, url: str) -> Series: ...

    def resolve_media(self, series: Series, episode: Episode) -> MediaSource: ...


@dataclass(frozen=True)
class SiteEntry:
    """How the registry recognises a site and builds its adapter."""

    name: str
    hosts: tuple[str, ...]
    create: Callable[[], Site]
