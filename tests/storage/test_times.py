from datetime import datetime, timedelta, timezone

import pytest

from tsuzuki.storage.times import from_text, to_text, utc_now


def test_round_trip() -> None:
    moment = datetime(2026, 11, 8, 12, 30, 5, tzinfo=timezone.utc)
    assert from_text(to_text(moment)) == moment


def test_other_timezones_are_stored_as_utc() -> None:
    lagos = timezone(timedelta(hours=1))
    moment = datetime(2026, 11, 8, 13, 0, tzinfo=lagos)
    assert to_text(moment) == "2026-11-08T12:00:00+00:00"


def test_naive_datetimes_are_refused() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        to_text(datetime(2026, 11, 8, 12, 0))


def test_text_sorts_like_time() -> None:
    earlier = to_text(datetime(2026, 1, 1, tzinfo=timezone.utc))
    later = to_text(datetime(2026, 12, 1, tzinfo=timezone.utc))
    assert earlier < later


def test_utc_now_is_aware() -> None:
    assert utc_now().tzinfo is not None
