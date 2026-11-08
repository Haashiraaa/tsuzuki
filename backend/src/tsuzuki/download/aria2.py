"""aria2c downloader: several connections per file, resumes partial files.

By default aria2c prints its own progress to the terminal and no ``ProgressEvent`` is emitted
(that is what the command line wants). With ``capture_progress`` its output is read instead and
turned into ``ProgressEvent``s, which is what the web server wants.
"""

import os
import re
import shutil
import subprocess
from collections.abc import Mapping

from tsuzuki.core.errors import DownloadError
from tsuzuki.core.events import ProgressEvent, ProgressHandler
from tsuzuki.core.models import DownloadJob
from tsuzuki.download.base import Outcome
from tsuzuki.net.http import merged_headers

EXECUTABLE = "aria2c"
DEFAULT_CONNECTIONS = 8


def is_available() -> bool:
    return shutil.which(EXECUTABLE) is not None


def header_args(headers: Mapping[str, str]) -> list[str]:
    """Map request headers to aria2c options."""
    args: list[str] = []
    for name, value in headers.items():
        lowered = name.lower()
        if lowered == "user-agent":
            args += ["--user-agent", value]
        elif lowered == "referer":
            args += ["--referer", value]
        else:
            args += ["--header", f"{name}: {value}"]
    return args


def build_command(job: DownloadJob, connections: int = DEFAULT_CONNECTIONS) -> list[str]:
    return [
        EXECUTABLE,
        "-x", str(connections),
        "-s", str(connections),
        "-c",  # continue a partial file instead of assuming it is complete
        "--allow-overwrite=true",  # needed alongside -c to touch an existing file
        "--auto-file-renaming=false",  # no "episode_5 (1).mp4" copies on retry
        *header_args(merged_headers(job.source.headers)),
        "-d", str(job.directory),
        "-o", job.filename,
        job.source.url,
    ]  # fmt: skip


class Aria2Downloader:
    def __init__(
        self, connections: int = DEFAULT_CONNECTIONS, *, capture_progress: bool = False
    ) -> None:
        self._connections = connections
        self._capture = capture_progress

    def download(self, job: DownloadJob, on_progress: ProgressHandler) -> Outcome:
        job.directory.mkdir(parents=True, exist_ok=True)
        command = build_command(job, self._connections)
        if self._capture:
            run_aria2_captured(command, job.filename, on_progress)
        else:
            run_aria2(command)
        return "downloaded"


def run_aria2(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise DownloadError(f"{EXECUTABLE} not found") from exc
    except subprocess.CalledProcessError as exc:
        raise DownloadError(f"{EXECUTABLE} exited with code {exc.returncode}") from exc


# aria2c's one-line readout looks like: [#2089b0 400KiB/33MiB(1%) CN:1 DL:115KiB ETA:4m51s]
READOUT = re.compile(
    r"\[#\w+ (?P<done>[\d.]+)(?P<du>[KMGT]?i?B)/(?P<total>[\d.]+)(?P<tu>[KMGT]?i?B)"
)
UNITS = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "TiB": 1024**4}
TAIL_CHARS = 300  # how much of aria2c's last output goes into an error message


def parse_readout(line: str, filename: str) -> ProgressEvent | None:
    """Bytes done and total from one aria2c readout line, or None if it is not one."""
    match = READOUT.search(line)
    if match is None:
        return None
    try:
        done = float(match["done"]) * UNITS[normalise_unit(match["du"])]
        total = float(match["total"]) * UNITS[normalise_unit(match["tu"])]
    except (KeyError, ValueError):
        return None
    return ProgressEvent(filename, int(done), int(total))


def normalise_unit(unit: str) -> str:
    """aria2c writes KiB/MiB; older builds wrote KB/MB. Both mean powers of 1024 here."""
    return unit if unit.endswith("iB") or unit == "B" else unit[:-1] + "iB"


def run_aria2_captured(command: list[str], filename: str, on_progress: ProgressHandler) -> None:
    """Run aria2c, report its progress, and stop it if ``on_progress`` raises (cancel, shutdown)."""
    try:
        process = subprocess.Popen(  # noqa: S603  (the command is built from our own parts)
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
    except FileNotFoundError as exc:
        raise DownloadError(f"{EXECUTABLE} not found") from exc
    stream = process.stdout
    if stream is None:  # cannot happen with stdout=PIPE; keeps the type checker honest
        process.kill()
        raise DownloadError(f"{EXECUTABLE}: no output to read")
    tail = ""
    pending = ""
    try:
        while True:
            chunk = os.read(stream.fileno(), 4096)
            if not chunk:
                break
            pending += chunk.decode("utf-8", errors="replace")
            *lines, pending = re.split(r"[\r\n]", pending)
            for line in lines:
                if not line.strip():
                    continue
                tail = (tail + "\n" + line)[-TAIL_CHARS:]
                event = parse_readout(line, filename)
                if event is not None:
                    on_progress(event)
        code = process.wait()
    except BaseException:
        process.kill()
        process.wait()
        raise
    if code != 0:
        raise DownloadError(f"{EXECUTABLE} exited with code {code}: {tail.strip()}")
