"""One visitor's library and the series pages in it."""

from typing import Literal

from fastapi import APIRouter, HTTPException

from tsuzuki.api.deps import State
from tsuzuki.api.ladder import built_in_steps
from tsuzuki.api.schemas import AddSeriesIn, SeriesDetailOut, SeriesOut
from tsuzuki.api.views import episode_view, series_view
from tsuzuki.api.visitor import RequiredVisitor, Visitor, Writer
from tsuzuki.core.errors import LimitError
from tsuzuki.storage import (
    add_to_library,
    get_series_by_url,
    get_summary,
    in_library,
    library_size,
    list_episodes,
    list_summaries,
    requests_for_series,
    sync_episodes,
    transaction,
    upsert_series,
)
from tsuzuki.storage.episodes import count_episodes

PAGE_SIZE = 12  # episodes shown before "show all"

router = APIRouter()


@router.get("/series")
def list_library(state: State, visitor: Visitor) -> list[SeriesOut]:
    if visitor is None:
        return []
    with state.database() as conn:
        return [series_view(summary) for summary in list_summaries(conn, visitor)]


@router.post("/series")
def add_series(body: AddSeriesIn, state: State, visitor: Writer) -> SeriesOut:
    """Put a series in this visitor's library. The series itself is shared: if somebody added it
    recently it is reused, otherwise the site is read again for the current episode list."""
    now = state.clock()
    limits = state.limits
    with state.database() as conn:
        known = get_series_by_url(conn, body.url)
        already_mine = known is not None and in_library(conn, visitor, known.id)
        if not already_mine and library_size(conn, visitor) >= limits.max_series:
            raise LimitError(
                f"Your library is full ({limits.max_series} series). Remove one before adding more."
            )
        fresh = known is not None and now - known.updated_at < limits.series_fresh_for
        if known is not None and fresh:
            series_id = known.id
        else:
            site = state.resolve_site(body.url)
            fetched = site.fetch_series(body.url)
            with transaction(conn):
                record = upsert_series(
                    conn, site=site.name, url=fetched.url, title=fetched.title, now=now
                )
                episodes = [(e.number, e.ref) for e in fetched.episodes]
                sync_episodes(conn, record.id, episodes, now)
            series_id = record.id
        with transaction(conn):
            add_to_library(conn, visitor, series_id, now)
        summary = get_summary(conn, visitor, series_id)
    if summary is None:
        raise HTTPException(500, "The series was saved but could not be read back")
    return series_view(summary)


@router.get("/series/{series_id}")
def get_series_page(
    series_id: int,
    state: State,
    visitor: RequiredVisitor,
    order: Literal["newest", "oldest"] = "newest",
    all: bool = False,  # the name is part of the URL the frontend uses
) -> SeriesDetailOut:
    with state.database() as conn:
        summary = get_summary(conn, visitor, series_id)
        if summary is None:
            raise HTTPException(404, f"Series {series_id} is not in your library")
        episodes = list_episodes(
            conn, series_id, newest_first=order == "newest", limit=None if all else PAGE_SIZE
        )
        listed = count_episodes(conn, series_id)
        mine = requests_for_series(conn, visitor, series_id)
    return SeriesDetailOut(
        series=series_view(summary),
        episodes=[episode_view(record, mine.get(record.id)) for record in episodes],
        listed=listed,
        steps=built_in_steps(summary.series.site),
    )
