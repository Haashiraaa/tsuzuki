"""Asking for episodes, and the queue screen. Everything here is about one visitor's own list."""

import sqlite3
from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, Response

from tsuzuki.api.deps import State, episode_or_404
from tsuzuki.api.schemas import QueueEpisodesIn, QueueOut
from tsuzuki.api.state import ApiState
from tsuzuki.api.views import queue_view
from tsuzuki.api.visitor import RequiredVisitor, Visitor, Writer
from tsuzuki.core.errors import InvalidTransitionError, LimitError
from tsuzuki.storage import (
    EpisodeStatus,
    cancel_request,
    get_episode,
    get_request,
    in_library,
    open_count,
    request_episode,
    transaction,
    view_status,
)
from tsuzuki.storage.records import OPEN_VIEW, REQUESTABLE_VIEW

router = APIRouter()

NO_CONTENT = 204
S = EpisodeStatus


def ask_for(
    state: ApiState,
    conn: sqlite3.Connection,
    visitor: int,
    episode_ids: Sequence[int],
    *,
    series_id: int | None = None,
) -> None:
    """Request episodes for one visitor, all or none: if they would go over their limit nothing
    is queued. Episodes the visitor already has open are skipped, so pressing twice is harmless."""
    wanted = list(dict.fromkeys(episode_ids))
    new: list[int] = []
    for episode_id in wanted:
        episode = get_episode(conn, episode_id)
        if episode is None or (series_id is not None and episode.series_id != series_id):
            raise HTTPException(404, f"Episode {episode_id} is not part of this series")
        if not in_library(conn, visitor, episode.series_id):
            raise HTTPException(404, f"Episode {episode_id} is not in your library")
        if view_status(episode.status, get_request(conn, visitor, episode_id)) in REQUESTABLE_VIEW:
            new.append(episode_id)
    limit = state.limits.max_open
    waiting = open_count(conn, visitor)
    if waiting + len(new) > limit:
        if waiting == 0:
            raise LimitError(f"You can queue up to {limit} episodes at a time. Pick fewer.")
        raise LimitError(
            f"You can have up to {limit} episodes waiting at once and already have {waiting}. "
            "Save or cancel some, then try again."
        )
    now = state.clock()
    with transaction(conn):
        for episode_id in new:
            request_episode(conn, visitor, episode_id, now, state.retention)


@router.post("/downloads", status_code=NO_CONTENT)
def queue_episodes(body: QueueEpisodesIn, state: State, visitor: Writer) -> Response:
    with state.database() as conn:
        if not in_library(conn, visitor, body.series_id):
            raise HTTPException(404, f"Series {body.series_id} is not in your library")
        ask_for(state, conn, visitor, body.episode_ids, series_id=body.series_id)
    return Response(status_code=NO_CONTENT)


@router.get("/queue")
def get_queue(state: State, visitor: Visitor) -> QueueOut:
    with state.database() as conn:
        return queue_view(
            conn, state.progress, visitor, downloads=state.root.downloads, slots=state.slots
        )


@router.post("/episodes/{episode_id}/retry", status_code=NO_CONTENT)
def retry(episode_id: int, state: State, visitor: RequiredVisitor) -> Response:
    episode = episode_or_404(state, episode_id)
    with state.database() as conn:
        mine = get_request(conn, visitor, episode_id)
        if view_status(episode.status, mine) not in REQUESTABLE_VIEW:
            raise InvalidTransitionError(f"Episode {episode_id} is {episode.status.value}")
        ask_for(state, conn, visitor, [episode_id])
    return Response(status_code=NO_CONTENT)


@router.post("/episodes/{episode_id}/cancel", status_code=NO_CONTENT)
def cancel(episode_id: int, state: State, visitor: RequiredVisitor) -> Response:
    """Withdraw this visitor's request. If nobody else wants the episode, a waiting one goes
    back to the library and a running one is asked to stop (the worker puts it back)."""
    episode = episode_or_404(state, episode_id)
    with state.database() as conn:
        mine = get_request(conn, visitor, episode_id)
        if view_status(episode.status, mine) not in OPEN_VIEW:
            raise InvalidTransitionError(f"Episode {episode_id} is {episode.status.value}")
        with transaction(conn):
            stop_download = cancel_request(conn, visitor, episode_id, state.clock())
    if stop_download:
        state.progress.request_cancel(episode_id)
    return Response(status_code=NO_CONTENT)


@router.post("/episodes/{episode_id}/pause")
def pause(episode_id: int) -> Response:
    raise HTTPException(501, "Pausing is not supported yet. Cancel it and queue it again.")
