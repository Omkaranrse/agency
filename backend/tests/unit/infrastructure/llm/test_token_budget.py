"""Unit tests for TokenBudget and TokenBudgetManager."""

import concurrent.futures

import pytest

from agency.infrastructure.llm.errors import TokenBudgetExceededError
from agency.infrastructure.llm.models import TokenUsage
from agency.infrastructure.llm.token_budget import TokenBudget, TokenBudgetManager


def test_token_budget_reservation_and_reconciliation() -> None:
    """Reservation decrements available budget and commits actual usage."""
    budget = TokenBudget(run_id="run-1", limit=10_000)

    # Check initial state
    summary = budget.get_summary()
    assert summary.budget_limit == 10_000
    assert summary.remaining_tokens == 10_000
    assert summary.total_tokens == 0

    # Reserve 2,000 tokens
    reservation = budget.reserve(2_000)
    assert reservation.amount == 2_000

    # Remaining tokens accounts for active reservation
    summary_mid = budget.get_summary()
    assert summary_mid.remaining_tokens == 8_000

    # Actual usage was 1,200 tokens
    actual = TokenUsage.create(input_tokens=400, output_tokens=800)
    budget.reconcile(reservation, actual_usage=actual)

    # Reservation is released, committed total is 1,200, remaining is 8,800
    summary_post = budget.get_summary()
    assert summary_post.input_tokens == 400
    assert summary_post.output_tokens == 800
    assert summary_post.total_tokens == 1_200
    assert summary_post.remaining_tokens == 8_800
    assert summary_post.call_count == 1


def test_token_budget_exceeded_raises_error() -> None:
    """Requesting more tokens than remaining budget raises TokenBudgetExceededError."""
    budget = TokenBudget(run_id="run-budget-test", limit=5_000)

    budget.reserve(4_000)

    # Attempting to reserve 2,000 when only 1,000 remains
    with pytest.raises(TokenBudgetExceededError) as exc_info:
        budget.reserve(2_000)

    assert exc_info.value.run_id == "run-budget-test"
    assert exc_info.value.requested_tokens == 2_000
    assert exc_info.value.remaining_tokens == 1_000


def test_token_budget_failed_call_conservative_accounting() -> None:
    """Failed calls without usage reporting use conservative accounting."""
    budget = TokenBudget(run_id="run-failed", limit=5_000)
    res = budget.reserve(2_000)

    # Provider failed with no usage reported
    budget.reconcile(res, actual_usage=None, conservative_fallback=500)

    summary = budget.get_summary()
    assert summary.total_tokens == 500
    assert summary.remaining_tokens == 4_500
    assert summary.call_count == 1


def test_token_budget_repair_and_fallback_counters() -> None:
    """Repair and fallback flags increment their respective metric counters."""
    budget = TokenBudget(run_id="run-counts", limit=20_000)

    r1 = budget.reserve(1_000)
    budget.reconcile(r1, TokenUsage.create(100, 200), is_repair=True)

    r2 = budget.reserve(1_000)
    budget.reconcile(r2, TokenUsage.create(150, 250), is_fallback=True)

    summary = budget.get_summary()
    assert summary.call_count == 2
    assert summary.repair_call_count == 1
    assert summary.fallback_call_count == 1


def test_token_budget_manager_run_isolation() -> None:
    """TokenBudgetManager maintains separate budgets per run_id."""
    manager = TokenBudgetManager(default_budget=10_000)

    res1 = manager.reserve("run-alpha", 3_000)
    res2 = manager.reserve("run-beta", 8_000)

    assert res1.run_id == "run-alpha"
    assert res2.run_id == "run-beta"

    sum_a = manager.get_summary("run-alpha")
    sum_b = manager.get_summary("run-beta")

    assert sum_a.remaining_tokens == 7_000
    assert sum_b.remaining_tokens == 2_000

    # Over-spending run-beta does not affect run-alpha
    with pytest.raises(TokenBudgetExceededError):
        manager.reserve("run-beta", 3_000)

    # run-alpha still has 7,000 available
    res1_b = manager.reserve("run-alpha", 4_000)
    assert res1_b.amount == 4_000


def test_token_budget_concurrent_reservations_safety() -> None:
    """Concurrent reservations across threads cannot exceed budget limit."""
    manager = TokenBudgetManager(default_budget=10_000, default_reservation=1_000)
    run_id = "concurrent-run"

    successful_reservations = 0
    rejected_reservations = 0

    def _attempt_reservation() -> None:
        nonlocal successful_reservations, rejected_reservations
        try:
            res = manager.reserve(run_id, amount=1_000)
            successful_reservations += 1
            # Simulate short work and reconcile
            manager.reconcile(res, TokenUsage.create(500, 500))
        except TokenBudgetExceededError:
            rejected_reservations += 1

    # Launch 20 concurrent threads against a budget of 10,000 (each requesting 1,000)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_attempt_reservation) for _ in range(20)]
        concurrent.futures.wait(futures)

    summary = manager.get_summary(run_id)
    # Total committed should not exceed 10,000
    assert summary.total_tokens <= 10_000
    assert successful_reservations <= 10
    assert successful_reservations + rejected_reservations == 20
