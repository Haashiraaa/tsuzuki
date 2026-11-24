"""Shared route plumbing."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from tsuzuki.api.state import ApiState
from tsuzuki.storage import EpisodeRecord, get_episode


def get_state(request: Request) -> ApiState:
    state: ApiState = request.app.state.tsuzuki
    return state


State = Annotated[ApiState, Depends(get_state)]


def episode_or_404(state: ApiState, episode_id: int) -> EpisodeRecord:
    with state.database() as conn:
        record = get_episode(conn, episode_id)
    if record is None:
        raise HTTPException(404, f"Episode {episode_id} does not exist")
    return record
