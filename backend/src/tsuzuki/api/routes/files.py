"""Getting a finished episode off the server.

``/file`` is "Save to this device": the browser downloads it, and only when every byte has
been sent does the server mark it delivered and delete its own copy. ``/stream`` plays it in
the browser (with seeking) and keeps the file.
"""

from collections.abc import Generator
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from tsuzuki.api.deps import State, episode_or_404
from tsuzuki.api.state import ApiState
from tsuzuki.storage import EpisodeRecord, EpisodeStatus, confirm_delivery

router = APIRouter()

CHUNK_BYTES = 1024 * 1024
MEDIA_TYPE = "video/mp4"
GONE = 410


def ready_file(state: ApiState, episode_id: int) -> tuple[EpisodeRecord, Path]:
    """The episode and its file, if it is ready and the file is really there and inside the
    downloads folder."""
    record = episode_or_404(state, episode_id)
    if record.status is not EpisodeStatus.READY or not record.file_path:
        raise HTTPException(409, f"Episode {episode_id} is {record.status.value}, not ready")
    path = Path(record.file_path).resolve()
    if not path.is_relative_to(state.root.downloads.resolve()):
        raise HTTPException(404, "File not found")
    if not path.is_file():
        raise HTTPException(GONE, "The file is no longer on the server. Queue it again.")
    return record, path


def send_then_deliver(state: ApiState, episode_id: int, path: Path) -> Generator[bytes]:
    """Yield the file; after the last byte, record the delivery and remove the server's copy.
    If the browser gives up half way, the generator is closed before that line and the file
    stays for another try."""
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            yield chunk
    with state.database() as conn:
        confirm_delivery(conn, state.root.downloads, episode_id, state.clock())


@router.get("/episodes/{episode_id}/file")
def save_to_device(episode_id: int, state: State) -> StreamingResponse:
    _record, path = ready_file(state, episode_id)
    name = quote(path.name)
    return StreamingResponse(
        send_then_deliver(state, episode_id, path),
        media_type=MEDIA_TYPE,
        headers={
            "Content-Length": str(path.stat().st_size),
            "Content-Disposition": f"attachment; filename=\"{name}\"; filename*=UTF-8''{name}",
        },
    )


@router.get("/episodes/{episode_id}/stream")
def play(episode_id: int, state: State) -> FileResponse:
    _record, path = ready_file(state, episode_id)
    return FileResponse(path, media_type=MEDIA_TYPE)
