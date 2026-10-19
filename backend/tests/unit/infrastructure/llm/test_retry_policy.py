"""Unit tests for rate-limit-aware retry policy with bounded backoff."""

import pytest

from agency.infrastructure.llm.errors import (
    AuthenticationError,
    ModelTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)
from agency.infrastructure.llm.retry_policy import RetryPolicy


def test_retry_policy_immediate_success() -> None:
    """Successful function executes once with zero sleep or retries."""
    slept: list[float] = []
    policy = RetryPolicy(
        max_retries=3,
        initial_delay_seconds=1.0,
        sleep_fn=slept.append,
        jitter_fn=lambda x: 0.0,
    )

    result, retries = policy.execute(lambda: "success")
    assert result == "success"
    assert retries == 0
    assert len(slept) == 0


def test_retry_policy_transient_error_recovered() -> None:
    """Transient error triggers backoff and succeeds on next attempt."""
    slept: list[float] = []
    attempts = 0

    def _flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RateLimitError("gemini", "Rate limit hit")
        return "recovered"

    policy = RetryPolicy(
        max_retries=3,
        initial_delay_seconds=1.0,
        backoff_multiplier=2.0,
        sleep_fn=slept.append,
        jitter_fn=lambda x: 0.0,
    )

    result, retries = policy.execute(_flaky)
    assert result == "recovered"
    assert retries == 1
    assert attempts == 2
    assert slept == [1.0]


def test_retry_policy_honors_retry_after() -> None:
    """Retry-After hint from provider overrides exponential backoff."""
    slept: list[float] = []
    attempts = 0

    def _rate_limited() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RateLimitError("gemini", "Rate limited", retry_after=5.5)
        return "done"

    policy = RetryPolicy(
        max_retries=3,
        initial_delay_seconds=1.0,
        sleep_fn=slept.append,
        jitter_fn=lambda x: 0.0,
    )

    result, retries = policy.execute(_rate_limited)
    assert result == "done"
    assert retries == 1
    assert slept == [5.5]


def test_retry_policy_exponential_backoff_and_capping() -> None:
    """Backoff doubles until reaching max_delay_seconds."""
    slept: list[float] = []
    attempts = 0

    def _always_timeout() -> str:
        nonlocal attempts
        attempts += 1
        raise ModelTimeoutError("ollama", "llama3", 10.0)

    policy = RetryPolicy(
        max_retries=4,
        initial_delay_seconds=1.0,
        max_delay_seconds=3.0,
        backoff_multiplier=2.0,
        sleep_fn=slept.append,
        jitter_fn=lambda x: 0.0,
    )

    with pytest.raises(ModelTimeoutError):
        policy.execute(_always_timeout)

    assert attempts == 5  # 1 initial + 4 retries
    # Delays: 1.0, 2.0, capped to 3.0, capped to 3.0
    assert slept == [1.0, 2.0, 3.0, 3.0]


def test_retry_policy_deadline_exceeded() -> None:
    """Overall request deadline stops further retries."""
    slept: list[float] = []
    current_time = 100.0

    def mock_time() -> float:
        return current_time

    def mock_sleep(d: float) -> None:
        nonlocal current_time
        current_time += d
        slept.append(d)

    def _flaky() -> str:
        raise ProviderUnavailableError("gemini", "Server 503")

    policy = RetryPolicy(
        max_retries=5,
        initial_delay_seconds=2.0,
        overall_deadline_seconds=5.0,
        time_fn=mock_time,
        sleep_fn=mock_sleep,
        jitter_fn=lambda x: 0.0,
    )

    with pytest.raises(ProviderUnavailableError):
        policy.execute(_flaky)

    # Attempt 1: fails at t=100. Delay=2.0. Sleeping 2.0 puts current_time=102.
    # Attempt 2: fails at t=102. Delay=4.0. 102+4 = 106 > 105 (deadline). Stops!
    assert len(slept) == 1
    assert slept == [2.0]


def test_retry_policy_non_transient_error_not_retried() -> None:
    """Authentication and client errors fail immediately without retry."""
    slept: list[float] = []
    attempts = 0

    def _auth_fail() -> str:
        nonlocal attempts
        attempts += 1
        raise AuthenticationError("gemini", "Invalid API key")

    policy = RetryPolicy(
        max_retries=3,
        sleep_fn=slept.append,
    )

    with pytest.raises(AuthenticationError):
        policy.execute(_auth_fail)

    assert attempts == 1
    assert len(slept) == 0
