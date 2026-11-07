"""aria2c downloader: several connections per file, resumes partial files.

aria2c prints its own progress to the terminal, so no ``ProgressEvent`` is emitted from here.
"""

import shutil
import subprocess
from collections.abc import Mapping

from tsuzuki.core.errors import DownloadError
from tsuzuki.core.events import ProgressHandler
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
    def __init__(self, connections: int = DEFAULT_CONNECTIONS) -> None:
        self._connections = connections

    def download(self, job: DownloadJob, on_progress: ProgressHandler) -> Outcome:
        job.directory.mkdir(parents=True, exist_ok=True)
        run_aria2(build_command(job, self._connections))
        return "downloaded"


def run_aria2(command: list[str]) -> None:
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise DownloadError(f"{EXECUTABLE} not found") from exc
    except subprocess.CalledProcessError as exc:
        raise DownloadError(f"{EXECUTABLE} exited with code {exc.returncode}") from exc
