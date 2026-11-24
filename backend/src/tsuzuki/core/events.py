"""Events the runner emits. Front-ends (CLI, web) decide how to show them."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SeriesEvent:
    kind: Literal["found", "failed"]
    url: str
    title: str = ""
    count: int = 0
    detail: str = ""


@dataclass(frozen=True)
class EpisodeEvent:
    kind: Literal["started", "skipped", "completed", "failed"]
    series: str
    episode: str
    detail: str = ""


@dataclass(frozen=True)
class ProgressEvent:
    """Cumulative bytes for one file. ``total`` is 0 when the server didn't say."""

    filename: str
    done: int
    total: int


Event = SeriesEvent | EpisodeEvent | ProgressEvent
EventHandler = Callable[[Event], None]
ProgressHandler = Callable[[ProgressEvent], None]


def ignore_events(_event: Event) -> None:
    """Default handler: drop everything."""
