"""Thread-safe per-run token budget enforcement, reservations, and reconciliation."""

import threading
import uuid
from dataclasses import dataclass

from agency.infrastructure.llm.errors import TokenBudgetExceededError
from agency.infrastructure.llm.models import TokenUsage, TokenUsageSummary


@dataclass(frozen=True)
class TokenReservation:
    """Represents a tentative token reservation before dispatching an LLM call."""

    reservation_id: str
    run_id: str
    amount: int


class TokenBudget:
    """Per-run token budget enforcing hard limits and tracking token consumption."""

    def __init__(self, run_id: str, limit: int) -> None:
        self.run_id = run_id
        self.limit = limit
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.call_count = 0
        self.repair_call_count = 0
        self.fallback_call_count = 0
        self._active_reservations: dict[str, int] = {}
        self._lock = threading.Lock()

    @property
    def reserved_tokens(self) -> int:
        """Total tokens currently reserved by in-flight calls."""
        with self._lock:
            return sum(self._active_reservations.values())

    @property
    def remaining_tokens(self) -> int:
        """Tokens available for new reservations or usage."""
        with self._lock:
            committed = self.total_tokens + sum(self._active_reservations.values())
            return max(0, self.limit - committed)

    def reserve(self, amount: int) -> TokenReservation:
        """Reserve a token allocation before dispatch.

        Raises:
            TokenBudgetExceededError: If the remaining budget cannot accommodate amount.
        """
        with self._lock:
            committed = self.total_tokens + sum(self._active_reservations.values())
            available = self.limit - committed
            if amount > available:
                raise TokenBudgetExceededError(
                    run_id=self.run_id,
                    requested=amount,
                    remaining=max(0, available),
                    budget=self.limit,
                )

            res_id = str(uuid.uuid4())
            self._active_reservations[res_id] = amount
            return TokenReservation(
                reservation_id=res_id, run_id=self.run_id, amount=amount
            )

    def reconcile(
        self,
        reservation: TokenReservation,
        actual_usage: TokenUsage | None = None,
        conservative_fallback: int = 500,
        is_repair: bool = False,
        is_fallback: bool = False,
    ) -> None:
        """Release reservation and commit actual token usage to budget."""
        with self._lock:
            self._active_reservations.pop(reservation.reservation_id, None)
            self.call_count += 1
            if is_repair:
                self.repair_call_count += 1
            if is_fallback:
                self.fallback_call_count += 1

            if actual_usage and actual_usage.total_tokens is not None:
                inp = actual_usage.input_tokens or 0
                out = actual_usage.output_tokens or 0
                tot = actual_usage.total_tokens
            elif actual_usage and (
                actual_usage.input_tokens or actual_usage.output_tokens
            ):
                inp = actual_usage.input_tokens or 0
                out = actual_usage.output_tokens or 0
                tot = inp + out
            else:
                # Conservative accounting when provider fails without reporting usage
                inp = 0
                out = min(reservation.amount, conservative_fallback)
                tot = out

            self.input_tokens += inp
            self.output_tokens += out
            self.total_tokens += tot

    def get_summary(self) -> TokenUsageSummary:
        """Produce a snapshot summary of current token consumption."""
        with self._lock:
            committed = self.total_tokens + sum(self._active_reservations.values())
            remaining = max(0, self.limit - committed)
            return TokenUsageSummary(
                run_id=self.run_id,
                input_tokens=self.input_tokens,
                output_tokens=self.output_tokens,
                total_tokens=self.total_tokens,
                budget_limit=self.limit,
                remaining_tokens=remaining,
                call_count=self.call_count,
                repair_call_count=self.repair_call_count,
                fallback_call_count=self.fallback_call_count,
            )


class TokenBudgetManager:
    """Manages process-local token budgets segregated by run_id."""

    def __init__(
        self, default_budget: int = 200_000, default_reservation: int = 2_000
    ) -> None:
        self.default_budget = default_budget
        self.default_reservation = default_reservation
        self._budgets: dict[str, TokenBudget] = {}
        self._lock = threading.Lock()

    def get_or_create(self, run_id: str, limit: int | None = None) -> TokenBudget:
        """Get or initialize the token budget for a specific run."""
        with self._lock:
            if run_id not in self._budgets:
                budget_limit = limit or self.default_budget
                self._budgets[run_id] = TokenBudget(run_id=run_id, limit=budget_limit)
            return self._budgets[run_id]

    def reserve(self, run_id: str, amount: int | None = None) -> TokenReservation:
        """Reserve token allocation for a run before making an LLM call."""
        budget = self.get_or_create(run_id)
        reservation_amount = amount or self.default_reservation
        return budget.reserve(reservation_amount)

    def reconcile(
        self,
        reservation: TokenReservation,
        actual_usage: TokenUsage | None = None,
        is_repair: bool = False,
        is_fallback: bool = False,
    ) -> None:
        """Reconcile reservation against reported or estimated usage."""
        budget = self.get_or_create(reservation.run_id)
        budget.reconcile(
            reservation=reservation,
            actual_usage=actual_usage,
            conservative_fallback=self.default_reservation,
            is_repair=is_repair,
            is_fallback=is_fallback,
        )

    def get_summary(self, run_id: str) -> TokenUsageSummary:
        """Get snapshot usage summary for a run."""
        budget = self.get_or_create(run_id)
        return budget.get_summary()

    def reset(self, run_id: str | None = None) -> None:
        """Reset budget tracking for a run or all runs."""
        with self._lock:
            if run_id:
                self._budgets.pop(run_id, None)
            else:
                self._budgets.clear()
