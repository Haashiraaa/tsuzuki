"""Plain data returned by the storage functions."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EpisodeStatus(str, Enum):
    """Where an episode is in its life. ``lifecycle.py`` says which moves are allowed."""

    AVAILABLE = "available"  # seen on the site, nothing done yet
    QUEUED = "queued"  # waiting for a free download slot
    DOWNLOADING = "downloading"
    READY = "ready"  # file is on the server, waiting to be saved to a device
    DELIVERED = "delivered"  # saved to a device; file removed from the server
    EXPIRED = "expired"  # nobody collected it in time; file removed from the server
    FAILED = "failed"


# Episodes that were fetched at some point, whether or not the file is still on the server.
DOWNLOADED = frozenset({EpisodeStatus.READY, EpisodeStatus.DELIVERED, EpisodeStatus.EXPIRED})
IN_PROGRESS = frozenset({EpisodeStatus.QUEUED, EpisodeStatus.DOWNLOADING})


@dataclass(frozen=True)
class SeriesRecord:
    id: int
    site: str
    url: str
    title: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class SeriesSummary:
    """A series with the counts the library screen shows."""

    series: SeriesRecord
    total: int
    downloaded: int
    in_progress: int
    failed: int


@dataclass(frozen=True)
class EpisodeRecord:
    id: int
    series_id: int
    number: str
    ordinal: float
    ref: str
    status: EpisodeStatus
    file_path: str | None
    size_bytes: int | None
    error: str | None
    attempts: int
    expires_at: datetime | None
    updated_at: datetime
