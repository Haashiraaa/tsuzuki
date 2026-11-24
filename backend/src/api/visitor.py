"""Who is asking. Each browser carries a random secret in a cookie; that secret is the visitor.

The middleware only *looks up* the cookie, so a crawler hitting the API creates nothing. A
visitor is created the first time someone does something that changes data (``visitor_for_write``)
and the cookie is added to that response.
"""

from http.cookies import SimpleCookie
from typing import Annotated

import anyio.to_thread
from fastapi import Depends, HTTPException, Request
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from tsuzuki.api.deps import State
from tsuzuki.api.state import ApiState
from tsuzuki.storage import create_visitor, find_visitor, touch_visitor

COOKIE = "tsuzuki_visitor"
YEAR_SECONDS = 365 * 24 * 60 * 60
RESTORE_PREFIX = "/api/restore/"


def read_cookie(scope: Scope) -> str | None:
    for name, value in scope["headers"]:
        if name == b"cookie":
            jar: SimpleCookie = SimpleCookie()
            try:
                jar.load(value.decode("latin-1"))
            except Exception:
                return None
            morsel = jar.get(COOKIE)
            return morsel.value if morsel else None
    return None


def cookie_header(token: str, *, secure: bool) -> str:
    parts = [f"{COOKIE}={token}", "Path=/", f"Max-Age={YEAR_SECONDS}", "HttpOnly", "SameSite=Lax"]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


class VisitorMiddleware:
    """Works out the visitor for each request and adds the cookie when one was just issued.

    A pure ASGI middleware rather than a decorator-style one, so streaming downloads are not
    buffered or cut off.
    """

    def __init__(self, app: ASGIApp, state: ApiState) -> None:
        self.app = app
        self.state = state

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        shared = scope.setdefault("state", {})
        shared["visitor_id"] = None
        shared["token"] = None
        token = read_cookie(scope)
        if token and not scope["path"].startswith(RESTORE_PREFIX):
            visitor_id = await anyio.to_thread.run_sync(self.lookup, token)
            if visitor_id is not None:
                shared["visitor_id"] = visitor_id
                shared["token"] = token

        async def send_with_cookie(message: Message) -> None:
            issued = shared.get("issue_token")
            if message["type"] == "http.response.start" and issued:
                headers = MutableHeaders(scope=message)
                secure = scope.get("scheme") == "https"
                headers.append("set-cookie", cookie_header(issued, secure=secure))
            await send(message)

        await self.app(scope, receive, send_with_cookie)

    def lookup(self, token: str) -> int | None:
        with self.state.database() as conn:
            return find_visitor(conn, token)


def current_visitor(request: Request) -> int | None:
    """The visitor, or None for a browser that has not done anything yet."""
    return request.state.visitor_id  # type: ignore[no-any-return]


def required_visitor(request: Request) -> int:
    visitor_id = current_visitor(request)
    if visitor_id is None:
        raise HTTPException(404, "Nothing here yet. Add a series first.")
    return visitor_id


def visitor_for_write(request: Request, state: State) -> int:
    """The visitor, created now if this is their first action."""
    now = state.clock()
    with state.database() as conn:
        existing = current_visitor(request)
        if existing is not None:
            touch_visitor(conn, existing, now)
            return existing
        visitor_id, token = create_visitor(conn, now)
    request.state.visitor_id = visitor_id
    request.state.token = token
    request.state.issue_token = token
    return visitor_id


Visitor = Annotated[int | None, Depends(current_visitor)]
RequiredVisitor = Annotated[int, Depends(required_visitor)]
Writer = Annotated[int, Depends(visitor_for_write)]
