"""The library and the series page."""

from typing import Literal

from fastapi import APIRouter, HTTPException

from tsuzuki.api.deps import State
from tsuzuki.api.ladder import built_in_steps
from tsuzuki.api.schemas import AddSeriesIn, SeriesDetailOut, SeriesOut
from tsuzuki.api.views import episode_view, series_view
from tsuzuki.storage import (
    get_summary,
    list_episodes,
    list_summaries,
    sync_episodes,
    transaction,
    upsert_series,
)
from tsuzuki.storage.episodes import count_episodes

PAGE_SIZE = 12  # episodes shown before "show all"

router = APIRouter()


@router.get("/series")
def list_library(state: State) -> list[SeriesOut]:
    with state.database() as conn:
        return [series_view(summary) for summary in list_summaries(conn)]


@router.post("/series")
def add_series(body: AddSeriesIn, state: State) -> SeriesOut:
    """Read a series page and remember it with all its episodes. Adding it again refreshes it."""
    site = state.resolve_site(body.url)
    fetched = site.fetch_series(body.url)
    now = state.clock()
    with state.database() as conn:
        with transaction(conn):
            record = upsert_series(
                conn, site=site.name, url=fetched.url, title=fetched.title, now=now
            )
            sync_episodes(conn, record.id, [(e.number, e.ref) for e in fetched.episodes], now)
        summary = get_summary(conn, record.id)
    if summary is None:
        raise HTTPException(500, "The series was saved but could not be read back")
    return series_view(summary)


@router.get("/series/{series_id}")
def get_series_page(
    series_id: int,
    state: State,
    order: Literal["newest", "oldest"] = "newest",
    all: bool = False,  # the name is part of the URL the frontend uses
) -> SeriesDetailOut:
    with state.database() as conn:
        summary = get_summary(conn, series_id)
        if summary is None:
            raise HTTPException(404, f"Series {series_id} does not exist")
        episodes = list_episodes(
            conn,
            series_id,
            newest_first=order == "newest",
            limit=None if all else PAGE_SIZE,
        )
        listed = count_episodes(conn, series_id)
    return SeriesDetailOut(
        series=series_view(summary),
        episodes=[episode_view(record) for record in episodes],
        listed=listed,
        steps=built_in_steps(summary.series.site),
    )
