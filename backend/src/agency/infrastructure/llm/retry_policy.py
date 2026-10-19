"""Rate-limit-aware and transient failure retry policy with bounded backoff."""

import random
import time
from collections.abc import Callable
from typing import TypeVar

from agency.infrastructure.llm.errors import (
    ModelTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)

R = TypeVar("R")


def default_jitter(base_delay: float) -> float:
    """Generate proportional jitter between 0 and 25% of base delay."""
    return random.uniform(0.0, base_delay * 0.25)


class RetryPolicy:
    """Configurable exponential backoff retry executor for transient LLM errors."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_seconds: float = 1.0,
        max_delay_seconds: float = 30.0,
        backoff_multiplier: float = 2.0,
        overall_deadline_seconds: float = 120.0,
        sleep_fn: Callable[[float], None] = time.sleep,
        jitter_fn: Callable[[float], float] = default_jitter,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_retries = max_retries
        self.initial_delay_seconds = initial_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self.overall_deadline_seconds = overall_deadline_seconds
        self.sleep_fn = sleep_fn
        self.jitter_fn = jitter_fn
        self.time_fn = time_fn

    @classmethod
    def is_transient_error(cls, exc: Exception) -> bool:
        """Determine if an exception represents a recoverable transient failure."""
        return isinstance(
            exc, RateLimitError | ProviderUnavailableError | ModelTimeoutError
        )

    def execute(
        self,
        operation: Callable[[], R],
        is_transient: Callable[[Exception], bool] | None = None,
        on_retry: Callable[[Exception, int, float], None] | None = None,
    ) -> tuple[R, int]:
        """Execute operation with rate-limit and transient error retries.

        Returns:
            A tuple of (operation_result, retry_count).
        """
        transient_predicate = is_transient or self.is_transient_error
        attempt = 0
        start_time = self.time_fn()

        while True:
            try:
                result = operation()
                return result, attempt
            except Exception as exc:
                if not transient_predicate(exc):
                    raise exc

                if attempt >= self.max_retries:
                    raise exc

                # Compute wait delay
                if isinstance(exc, RateLimitError) and exc.retry_after is not None:
                    delay = min(exc.retry_after, self.max_delay_seconds)
                else:
                    base = self.initial_delay_seconds * (
                        self.backoff_multiplier**attempt
                    )
                    jitter = self.jitter_fn(base)
                    delay = min(base + jitter, self.max_delay_seconds)

                # Check deadline
                elapsed = self.time_fn() - start_time
                if elapsed + delay > self.overall_deadline_seconds:
                    raise exc

                attempt += 1
                if on_retry:
                    on_retry(exc, attempt, delay)

                self.sleep_fn(delay)
