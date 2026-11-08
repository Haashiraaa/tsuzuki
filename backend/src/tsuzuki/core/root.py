"""Where Tsuzuki keeps downloads and logs.

Strategies are tried in order and the first that applies wins:

1. ``--output`` on the command line
2. the ``TSUZUKI_HOME`` environment variable
3. the project folder, found with haashi's ``get_ancestor_by_name`` (works from a git clone)
4. ``~/tsuzuki`` (the normal case after a plain ``pip install``)
"""

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from haashi.utility import FileHandler, Logger

APP_NAME = "tsuzuki"
ENV_HOME = "TSUZUKI_HOME"
PROJECT_MARKER = "pyproject.toml"


@dataclass(frozen=True)
class Root:
    """The chosen folder and a human-readable note on why it was chosen."""

    path: Path
    source: str

    @property
    def downloads(self) -> Path:
        return self.path / "Downloads"

    @property
    def logs(self) -> Path:
        return self.path / "logs"

    @property
    def database(self) -> Path:
        return self.path / "tsuzuki.db"


def resolve_root(
    explicit: Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
    start: Path | None = None,
    home: Path | None = None,
) -> Root:
    """Pick the root folder. Arguments after ``explicit`` exist so tests can inject them."""
    environment = os.environ if env is None else env
    found = (
        from_explicit(explicit)
        or from_env(environment)
        or from_project_folder(start or Path(__file__).resolve().parent)
    )
    return found or from_home(home or Path.home())


def from_explicit(explicit: Path | None) -> Root | None:
    if explicit is None:
        return None
    return Root(explicit.expanduser().resolve(), "--output")


def from_env(env: Mapping[str, str]) -> Root | None:
    value = env.get(ENV_HOME)
    if not value:
        return None
    return Root(Path(value).expanduser().resolve(), f"${ENV_HOME}")


def from_project_folder(start: Path) -> Root | None:
    path = find_project_root(quiet_file_handler(), start)
    return Root(path, "project folder") if path else None


def from_home(home: Path) -> Root:
    return Root(home / APP_NAME, "home folder")


def find_project_root(handler: FileHandler, start: Path, name: str = APP_NAME) -> Path | None:
    """Nearest ancestor called ``name`` that also holds ``pyproject.toml``.

    The package folder ``backend/src/tsuzuki`` has the same name as the repo, so the plain
    name match would stop there. The marker file skips it and keeps climbing.
    """
    current = start
    while True:
        found = handler.get_ancestor_by_name(name, start_path=current)
        if found is None:
            return None
        if (found / PROJECT_MARKER).is_file():
            return found
        if found.parent == found:
            return None
        current = found.parent


def quiet_file_handler() -> FileHandler:
    """A FileHandler that stays silent when the lookup finds nothing (that's a normal case)."""
    return FileHandler(logger=Logger(logging.CRITICAL))
