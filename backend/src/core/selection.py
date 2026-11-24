"""Pick which episodes to download. Pure functions, no I/O."""

from collections.abc import Sequence

from tsuzuki.core.errors import EpisodeNotFoundError
from tsuzuki.core.models import Episode, Selection


def select_episodes(episodes: Sequence[Episode], selection: Selection) -> list[Episode]:
    """Apply ``--episode`` / ``--limit`` / ``--oldest`` to the episodes in listed order.

    The site lists newest first, so "newest" is the head of the list.
    """
    if selection.episode is not None:
        return [find_episode(episodes, selection.episode)]
    if selection.limit is not None:
        return take(episodes, selection.limit, selection.newest_first)
    return list(episodes)


def find_episode(episodes: Sequence[Episode], number: int) -> Episode:
    for episode in episodes:
        if number_matches(episode.number, number):
            return episode
    raise EpisodeNotFoundError(f"Episode {number} not found")


def number_matches(text: str, number: int) -> bool:
    """``"05"`` and ``"5"`` both match 5; non-numeric labels never match."""
    try:
        return int(text) == number
    except ValueError:
        return False


def take(episodes: Sequence[Episode], limit: int, newest_first: bool) -> list[Episode]:
    chosen = episodes[:limit] if newest_first else episodes[-limit:]
    return list(chosen)
