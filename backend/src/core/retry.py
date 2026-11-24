"""Retry with capped, jittered exponential backoff. Only retries errors that can heal."""

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from tsuzuki.core.errors import ConfigError, TsuzukiError

T = TypeVar("T")

# (attempt that just failed, total attempts, the error, seconds until the next try)
RetryNotice = Callable[[int, int, BaseException, float], None]


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 5
    base_delay: float = 2.0
    max_delay: float = 30.0

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ConfigError(f"attempts must be 1 or greater, got {self.attempts}")


def is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, TsuzukiError) and exc.retryable


def backoff_delay(
    policy: RetryPolicy, attempt: int, rng: Callable[[], float] = random.random
) -> float:
    """Half the capped exponential delay, plus up to the other half at random."""
    ceiling = min(policy.max_delay, policy.base_delay * 2 ** (attempt - 1))
    return ceiling / 2 + rng() * ceiling / 2


def retry_call(
    func: Callable[[], T],
    policy: RetryPolicy,
    *,
    on_retry: RetryNotice | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``func`` until it succeeds, a non-retryable error occurs, or attempts run out."""
    attempt = 1
    while True:
        try:
            return func()
        except Exception as exc:
            if attempt >= policy.attempts or not is_retryable(exc):
                raise
            delay = backoff_delay(policy, attempt)
            if on_retry is not None:
                on_retry(attempt, policy.attempts, exc, delay)
            sleep(delay)
            attempt += 1
