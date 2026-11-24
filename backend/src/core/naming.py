"""Turn scraped text into safe folder and file names."""

import re

from tsuzuki.core.errors import ParseError

_FOLDER_UNSAFE = re.compile(r"[^\w\s-]")
_FOLDER_SPACES = re.compile(r"[\s-]+")
_FILE_UNSAFE = re.compile(r"[^\w.-]")


def folder_name(title: str, fallback: str = "Unknown") -> str:
    """Series title -> folder name: letters, digits and single dashes only."""
    cleaned = _FOLDER_UNSAFE.sub("", title)
    cleaned = _FOLDER_SPACES.sub("-", cleaned).strip("-")
    return cleaned or fallback


def episode_filename(number: str, extension: str = "mp4") -> str:
    """Episode number -> ``episode_<number>.<ext>`` with path separators and junk removed."""
    safe = _FILE_UNSAFE.sub("_", number.strip()).strip("._")
    if not safe:
        raise ParseError(f"Episode number {number!r} cannot be used in a file name")
    return f"episode_{safe}.{extension}"
