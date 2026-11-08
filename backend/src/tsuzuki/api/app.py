"""Build the FastAPI application."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tsuzuki.api.routes import downloads, files, series, sites
from tsuzuki.api.state import ApiState
from tsuzuki.core.errors import (
    ConfigError,
    DownloadError,
    FetchError,
    InvalidTransitionError,
    ParseError,
    SiteNotSupportedError,
    StorageError,
    TsuzukiError,
)
from tsuzuki.storage import sweep_expired

log = logging.getLogger("tsuzuki.api")

SWEEP_EVERY_SECONDS = 600

# Which HTTP status each kind of Tsuzuki error becomes. More specific classes come first.
STATUS_FOR: list[tuple[type[TsuzukiError], int]] = [
    (InvalidTransitionError, 409),
    (StorageError, 500),
    (ConfigError, 422),
    (SiteNotSupportedError, 422),
    (FetchError, 502),
    (ParseError, 502),
    (DownloadError, 502),
]


def status_for(error: TsuzukiError) -> int:
    for kind, status in STATUS_FOR:
        if isinstance(error, kind):
            return status
    return 400


def sweep_once(state: ApiState) -> int:
    """Remove files nobody collected in time. Returns how many expired."""
    with state.database() as conn:
        return len(sweep_expired(conn, state.root.downloads, state.clock()))


async def sweep_forever(state: ApiState) -> None:
    while True:
        try:
            expired = await asyncio.to_thread(sweep_once, state)
            if expired:
                log.info("Removed %d uncollected file(s)", expired)
        except Exception:  # keep the loop alive; the next round tries again
            log.exception("Clean-up of uncollected files failed")
        await asyncio.sleep(SWEEP_EVERY_SECONDS)


def create_app(state: ApiState, *, sweep: bool = True) -> FastAPI:
    state.prepare()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        task = asyncio.create_task(sweep_forever(state)) if sweep else None
        try:
            yield
        finally:
            if task:
                task.cancel()

    app = FastAPI(
        title="Tsuzuki", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json"
    )
    app.state.tsuzuki = state

    @app.exception_handler(TsuzukiError)
    def tsuzuki_error(_request: Request, error: TsuzukiError) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        return JSONResponse({"detail": str(error)}, status_code=status_for(error))

    for module in (series, downloads, files, sites):
        app.include_router(module.router, prefix="/api")
    return app
