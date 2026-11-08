import pytest

from tsuzuki.core.errors import ConfigError, DownloadError, FetchError
from tsuzuki.core.retry import RetryPolicy, backoff_delay, is_retryable, retry_call


class Flaky:
    """Fails ``times`` times with ``error``, then returns "ok"."""

    def __init__(self, times: int, error: Exception) -> None:
        self.times, self.error, self.calls = times, error, 0

    def __call__(self) -> str:
        self.calls += 1
        if self.calls <= self.times:
            raise self.error
        return "ok"


class TestBackoff:
    def test_is_between_half_and_all_of_the_ceiling(self) -> None:
        policy = RetryPolicy(base_delay=2.0, max_delay=30.0)
        assert backoff_delay(policy, 1, rng=lambda: 0.0) == 1.0
        assert backoff_delay(policy, 1, rng=lambda: 1.0) == 2.0
        assert backoff_delay(policy, 3, rng=lambda: 1.0) == 8.0

    def test_is_capped(self) -> None:
        policy = RetryPolicy(base_delay=2.0, max_delay=30.0)
        assert backoff_delay(policy, 20, rng=lambda: 1.0) == 30.0


class TestPolicy:
    def test_needs_at_least_one_attempt(self) -> None:
        with pytest.raises(ConfigError):
            RetryPolicy(attempts=0)

    def test_which_errors_can_heal(self) -> None:
        assert is_retryable(DownloadError("cut off"))
        assert is_retryable(FetchError("503", retryable=True))
        assert not is_retryable(FetchError("404", retryable=False))
        assert not is_retryable(ValueError("bug"))


class TestRetryCall:
    def test_first_try_success_never_sleeps(self) -> None:
        slept: list[float] = []
        assert retry_call(lambda: "ok", RetryPolicy(), sleep=slept.append) == "ok"
        assert slept == []

    def test_retries_a_retryable_error_until_it_works(self) -> None:
        flaky = Flaky(2, DownloadError("cut off"))
        slept: list[float] = []
        notices: list[tuple[int, int]] = []
        result = retry_call(
            flaky,
            RetryPolicy(attempts=5),
            on_retry=lambda attempt, total, exc, delay: notices.append((attempt, total)),
            sleep=slept.append,
        )
        assert (result, flaky.calls, len(slept)) == ("ok", 3, 2)
        assert notices == [(1, 5), (2, 5)]

    def test_gives_up_after_the_last_attempt(self) -> None:
        flaky = Flaky(10, DownloadError("cut off"))
        with pytest.raises(DownloadError):
            retry_call(flaky, RetryPolicy(attempts=3), sleep=lambda _: None)
        assert flaky.calls == 3

    def test_does_not_retry_errors_that_cannot_heal(self) -> None:
        flaky = Flaky(10, FetchError("404", retryable=False))
        with pytest.raises(FetchError):
            retry_call(flaky, RetryPolicy(attempts=5), sleep=lambda _: None)
        assert flaky.calls == 1

    def test_does_not_hide_unexpected_errors(self) -> None:
        flaky = Flaky(10, ValueError("bug"))
        with pytest.raises(ValueError):
            retry_call(flaky, RetryPolicy(attempts=5), sleep=lambda _: None)
        assert flaky.calls == 1
