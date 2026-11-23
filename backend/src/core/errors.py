"""Exception hierarchy. ``retryable`` tells the retry helper whether trying again can help."""


class TsuzukiError(Exception):
    """Base class for every error Tsuzuki raises on purpose."""

    retryable: bool = False


class ConfigError(TsuzukiError):
    """Bad options or settings supplied by the user."""


class SiteNotSupportedError(TsuzukiError):
    """No site adapter handles the given URL."""


class EpisodeNotFoundError(TsuzukiError):
    """The requested episode is not on the series page."""


class ParseError(TsuzukiError):
    """A page did not look the way the site adapter expects (may be a transient bad page)."""

    retryable = True


class StorageError(TsuzukiError):
    """The local database could not be opened, migrated or updated."""


class InvalidTransitionError(StorageError):
    """An episode was asked to move to a status it cannot reach from where it is."""


class DownloadError(TsuzukiError):
    """A download failed or produced an incomplete file."""

    retryable = True


class FetchError(TsuzukiError):
    """A network request failed. Transient failures (timeouts, 5xx, 429) are retryable."""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class DownloadCancelled(TsuzukiError):
    """Someone cancelled this download while it was running."""


class DownloadInterrupted(TsuzukiError):
    """The server is shutting down. The download goes back in the queue and resumes later."""


class LimitError(TsuzukiError):
    """A visitor asked for more than the server allows at once. The message says what to do."""
