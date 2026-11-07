"""Small URL helpers."""

from urllib.parse import urlparse

from tsuzuki.core.errors import ConfigError
from tsuzuki.core.models import ALLOWED_SCHEMES


def origin(url: str) -> str:
    """``https://host/path?x`` -> ``https://host/``."""
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}/"


def hostname(url: str) -> str:
    """Lower-cased host of an http(s) URL. Raises ``ConfigError`` for anything else."""
    parts = urlparse(url)
    if parts.scheme not in ALLOWED_SCHEMES or not parts.hostname:
        raise ConfigError(f"Not a valid http(s) URL: {url!r}")
    return parts.hostname.lower()
