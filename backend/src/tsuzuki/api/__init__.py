"""The web API the frontend talks to. Start it with ``python -m tsuzuki.api``.

It is a thin layer: every route reads or changes the SQLite storage and nothing else. The
background worker that actually runs downloads is separate and reports progress through the
``ProgressBoard``.
"""

from tsuzuki.api.app import create_app
from tsuzuki.api.state import ApiState, Limits

__all__ = ["ApiState", "Limits", "create_app"]
