"""Asking for episodes, and the queue screen."""

from fastapi import APIRouter, HTTPException, Response

from tsuzuki.api.deps import State, episode_or_404
from tsuzuki.api.schemas import QueueEpisodesIn, QueueOut
from tsuzuki.api.views import queue_view
from tsuzuki.core.errors import InvalidTransitionError
from tsuzuki.storage import EpisodeStatus, get_episode, lifecycle, transaction

router = APIRouter()

NO_CONTENT = 204
S = EpisodeStatus

# Episodes that can be asked for (again). Anything already queued, running or waiting to be
# collected is left alone, so pressing the button twice does no harm.
REQUESTABLE = frozenset({S.AVAILABLE, S.FAILED, S.DELIVERED, S.EXPIRED})


@router.post("/downloads", status_code=NO_CONTENT)
def queue_episodes(body: QueueEpisodesIn, state: State) -> Response:
    now = state.clock()
    with state.database() as conn, transaction(conn):
        for episode_id in body.episode_ids:
            record = get_episode(conn, episode_id)
            if record is None or record.series_id != body.series_id:
                raise HTTPException(404, f"Episode {episode_id} is not part of this series")
            if record.status in REQUESTABLE:
                lifecycle.queue(conn, record.id, now)
    return Response(status_code=NO_CONTENT)


@router.get("/queue")
def get_queue(state: State) -> QueueOut:
    with state.database() as conn:
        return queue_view(conn, state.progress, downloads=state.root.downloads, slots=state.slots)


@router.post("/episodes/{episode_id}/retry", status_code=NO_CONTENT)
def retry(episode_id: int, state: State) -> Response:
    record = episode_or_404(state, episode_id)
    if record.status not in REQUESTABLE:
        raise InvalidTransitionError(f"Episode {episode_id} is {record.status.value}")
    with state.database() as conn, transaction(conn):
        lifecycle.queue(conn, episode_id, state.clock())
    return Response(status_code=NO_CONTENT)


@router.post("/episodes/{episode_id}/cancel", status_code=NO_CONTENT)
def cancel(episode_id: int, state: State) -> Response:
    """A waiting episode goes back to the library. A running one is asked to stop; the worker
    notices the request and puts it back."""
    record = episode_or_404(state, episode_id)
    if record.status is S.QUEUED:
        with state.database() as conn, transaction(conn):
            lifecycle.cancel(conn, episode_id, state.clock())
    elif record.status is S.DOWNLOADING:
        state.progress.request_cancel(episode_id)
    else:
        raise InvalidTransitionError(f"Episode {episode_id} is {record.status.value}")
    return Response(status_code=NO_CONTENT)


@router.post("/episodes/{episode_id}/pause")
def pause(episode_id: int) -> Response:
    raise HTTPException(501, "Pausing is not supported yet. Cancel it and queue it again.")
