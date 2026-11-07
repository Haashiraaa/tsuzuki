import pytest

from tsuzuki.core.errors import EpisodeNotFoundError
from tsuzuki.core.models import Episode, Selection
from tsuzuki.core.selection import number_matches, select_episodes

# the site lists newest first
EPISODES = tuple(Episode(number=str(n), ref=f"r{n}") for n in (12, 11, 10, 9))


def numbers(chosen: list[Episode]) -> list[str]:
    return [e.number for e in chosen]


def test_no_options_means_everything() -> None:
    assert numbers(select_episodes(EPISODES, Selection())) == ["12", "11", "10", "9"]


def test_one_episode_by_number() -> None:
    assert numbers(select_episodes(EPISODES, Selection(episode=10))) == ["10"]


def test_missing_episode_is_reported() -> None:
    with pytest.raises(EpisodeNotFoundError, match="42"):
        select_episodes(EPISODES, Selection(episode=42))


def test_limit_takes_the_newest_by_default() -> None:
    assert numbers(select_episodes(EPISODES, Selection(limit=2))) == ["12", "11"]


def test_limit_can_take_the_oldest() -> None:
    assert numbers(select_episodes(EPISODES, Selection(limit=2, newest_first=False))) == [
        "10",
        "9",
    ]


def test_limit_larger_than_the_list_returns_all() -> None:
    assert len(select_episodes(EPISODES, Selection(limit=99))) == 4


@pytest.mark.parametrize(
    ("text", "number", "expected"),
    [
        ("05", 5, True),
        ("5", 5, True),
        ("6", 5, False),
        ("SP1", 1, False),
        ("", 1, False),
    ],
)
def test_number_matching(text: str, number: int, expected: bool) -> None:
    assert number_matches(text, number) is expected
