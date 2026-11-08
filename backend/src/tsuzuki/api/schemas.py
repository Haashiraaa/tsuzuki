"""The JSON the frontend expects. Field names are camelCase on the wire, to match
``frontend/src/api/types.ts``; in Python they are snake_case."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Wire(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


EpisodeStatusName = Literal[
    "available", "queued", "downloading", "ready", "delivered", "expired", "failed"
]


class SeriesOut(Wire):
    id: int
    title: str
    site: str
    url: str
    total: int
    downloaded: int
    in_progress: int
    failed: int


class EpisodeOut(Wire):
    id: int
    number: str
    status: EpisodeStatusName


class StepOut(Wire):
    title: str
    outcome: Literal["worked", "skipped", "missing"]
    summary: str
    detail: str


class SeriesDetailOut(Wire):
    series: SeriesOut
    episodes: list[EpisodeOut]
    listed: int
    steps: list[StepOut]


class ActiveOut(Wire):
    id: int
    name: str
    method: str
    percent: int
    bytes_done: int
    bytes_total: int
    bytes_per_second: int
    eta_seconds: int | None


class WaitingOut(Wire):
    id: int
    name: str
    note: str
    failed: bool


class FinishedOut(Wire):
    id: int
    name: str


class QueueOut(Wire):
    active: list[ActiveOut]
    waiting: list[WaitingOut]
    finished: list[FinishedOut]
    slots: int
    downloads_folder: str
    example_file: str


class SiteOut(Wire):
    host: str
    how: str
    state: Literal["working", "needs-look"]


class SiteTestOut(Wire):
    host: str
    steps: list[StepOut]
    profile_path: str | None


class AddSeriesIn(Wire):
    url: str


class QueueEpisodesIn(Wire):
    series_id: int
    episode_ids: list[int]


class SiteUrlIn(Wire):
    url: str


class MeOut(Wire):
    restore_path: str | None
