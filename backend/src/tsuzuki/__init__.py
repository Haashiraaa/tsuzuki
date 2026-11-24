"""Tsuzuki: a personal anime downloader."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tsuzuki")
except PackageNotFoundError:  # running from a source tree that isn't installed
    __version__ = "0+unknown"
