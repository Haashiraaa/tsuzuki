"""Compatibility namespace for imports used before the backend package restructure.

The implementation now lives in :mod:`backend.src`. Expose the same package directory under
`tsuzuki` so existing integrations and downstream imports continue to work.
"""

from backend import src as _implementation

__path__ = list(_implementation.__path__)
__version__ = _implementation.__version__
