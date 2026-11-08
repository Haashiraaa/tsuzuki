"""Live download progress, kept in memory.

Progress changes many times a second and is worthless after a restart, so it is not written to
the database. The worker calls ``update``; the queue screen reads ``get``. ``request_cancel``
is how a route asks the worker to stop a download that is already running.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

SMOOTHING = 0.3  # weight of the newest speed sample; the rest comes from the history


@dataclass(frozen=True)
class Progress:
    method: str
    bytes_done: int
    bytes_total: int  # 0 when the site did not say
    bytes_per_second: float

    @property
    def percent(self) -> int:
        if self.bytes_total <= 0:
            return 0
        return min(100, int(self.bytes_done * 100 / self.bytes_total))

    @property
    def eta_seconds(self) -> int | None:
        if self.bytes_total <= 0 or self.bytes_per_second <= 0:
            return None
        return max(0, int((self.bytes_total - self.bytes_done) / self.bytes_per_second))


@dataclass
class _Entry:
    method: str
    done: int
    total: int
    speed: float
    seen_at: float


class ProgressBoard:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: dict[int, _Entry] = {}
        self._cancel: set[int] = set()

    def update(self, episode_id: int, *, done: int, total: int, method: str | None = None) -> None:
        now = self._clock()
        with self._lock:
            entry = self._entries.get(episode_id)
            if entry is None:
                self._entries[episode_id] = _Entry(method or "", done, total, 0.0, now)
                return
            elapsed = now - entry.seen_at
            if elapsed > 0 and done >= entry.done:
                sample = (done - entry.done) / elapsed
                entry.speed = (
                    sample
                    if entry.speed == 0
                    else (SMOOTHING * sample + (1 - SMOOTHING) * entry.speed)
                )
            entry.done, entry.total, entry.seen_at = done, total, now
            if method:
                entry.method = method

    def get(self, episode_id: int) -> Progress | None:
        with self._lock:
            entry = self._entries.get(episode_id)
            if entry is None:
                return None
            return Progress(entry.method, entry.done, entry.total, entry.speed)

    def clear(self, episode_id: int) -> None:
        """The download ended one way or another: forget its progress and any cancel request."""
        with self._lock:
            self._entries.pop(episode_id, None)
            self._cancel.discard(episode_id)

    def request_cancel(self, episode_id: int) -> None:
        with self._lock:
            self._cancel.add(episode_id)

    def cancel_requested(self, episode_id: int) -> bool:
        with self._lock:
            return episode_id in self._cancel
