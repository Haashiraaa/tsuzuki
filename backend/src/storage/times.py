"""Timestamps are stored as ISO-8601 text in UTC, so they sort correctly as plain strings."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_text(moment: datetime) -> str:
    """Text for a timezone-aware moment. A naive datetime is refused: it would be ambiguous."""
    if moment.tzinfo is None:
        raise ValueError("Timestamps must be timezone-aware")
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def from_text(text: str) -> datetime:
    return datetime.fromisoformat(text)
