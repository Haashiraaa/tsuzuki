"""Who you are, and how to get your library back on another device or after clearing cookies."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from tsuzuki.api.deps import State
from tsuzuki.api.schemas import MeOut
from tsuzuki.api.visitor import RESTORE_PREFIX, Visitor
from tsuzuki.storage import find_visitor

router = APIRouter()


@router.get("/me")
def me(request: Request, visitor: Visitor) -> MeOut:
    """``restore_path`` is a private link: whoever opens it gets this library. Null until the
    visitor has done something, because until then there is nothing to restore."""
    token = request.state.token
    if visitor is None or not token:
        return MeOut(restore_path=None)
    return MeOut(restore_path=f"{RESTORE_PREFIX}{token}")


@router.get("/restore/{token}")
def restore(token: str, request: Request, state: State) -> RedirectResponse:
    with state.database() as conn:
        found = find_visitor(conn, token)
    if found is None:
        raise HTTPException(404, "This restore link is not valid.")
    request.state.issue_token = token
    return RedirectResponse("/", status_code=303)
