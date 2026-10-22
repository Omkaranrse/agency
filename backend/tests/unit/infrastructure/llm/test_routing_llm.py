"""Unit tests for role-based RoutingLLM with fallback and budget enforcement."""

import pytest
from pydantic import BaseModel
from tests.fakes.fake_llm import FakeLLM

from agency.infrastructure.llm.errors import (
    AuthenticationError,
    FallbackExhaustedError,
    InvalidRoleError,
    ProviderUnavailableError,
    RateLimitError,
    StructuredOutputError,
    TokenBudgetExceededError,
)
from agency.infrastructure.llm.models import (
    AgentRole,
    GenerationRequest,
)
from agency.infrastructure.llm.routing_llm import RoutingLLM
from agency.infrastructure.llm.settings import LLMSettings
from agency.infrastructure.llm.token_budget import TokenBudgetManager


class MockPlan(BaseModel):
    step: str
    priority: int


def test_routing_llm_dispatches_to_primary_provider() -> None:
    """Primary provider configured for role handles the generation request."""
    fake_gemini = FakeLLM(provider_name="gemini", model_name="gemini-1.5-pro")
    fake_ollama = FakeLLM(provider_name="ollama", model_name="llama3.1:8b")

    mock_resp = MockPlan(step="Design architecture", priority=1)
    fake_gemini.set_response(MockPlan, mock_resp)

    # Configure PM role: primary=gemini, fallback=ollama (default in LLMSettings)
    settings = LLMSettings()
    budget = TokenBudgetManager(default_budget=50_000)

    router = RoutingLLM(
        providers={"gemini": fake_gemini, "ollama": fake_ollama},
        settings=settings,
        budget_manager=budget,
    )

    req = GenerationRequest[MockPlan](
        schema_type=MockPlan,
        prompt="Plan the sprint",
        role=AgentRole.PM,
        run_id="run-router-1",
    )

    result = router.generate(req)

    assert result.data.step == "Design architecture"
    assert result.provider == "gemini"
    assert result.fallback_occurred is False
    assert result.fallback_reason is None
    assert len(fake_gemini.calls) == 1
    assert len(fake_ollama.calls) == 0

    # Token budget was reconciled
    summary = budget.get_summary("run-router-1")
    assert summary.call_count == 1
    assert summary.fallback_call_count == 0


def test_routing_llm_invalid_role_rejected() -> None:
    """Unsupported agent role raises InvalidRoleError before dispatching."""
    router = RoutingLLM(providers={})
    req = GenerationRequest[MockPlan](
        schema_type=MockPlan,
        prompt="Do something",
        role="hacker_agent",
    )

    with pytest.raises(InvalidRoleError) as exc_info:
        router.generate(req)

    assert exc_info.value.role == "hacker_agent"


def test_routing_llm_fallback_on_transient_failure() -> None:
    """Transient failure on primary provider triggers explicit observable fallback."""
    fake_gemini = FakeLLM(provider_name="gemini", model_name="gemini-1.5-pro")
    fake_ollama = FakeLLM(provider_name="ollama", model_name="llama3.1:8b")

    # Primary fails with transient RateLimitError
    fake_gemini.set_failure(
        RateLimitError("gemini", "Quota exceeded", retry_after=10.0)
    )

    # Fallback succeeds
    fallback_resp = MockPlan(step="Fallback plan via Ollama", priority=2)
    fake_ollama.set_response(MockPlan, fallback_resp)

    settings = LLMSettings()
    budget = TokenBudgetManager(default_budget=50_000)

    router = RoutingLLM(
        providers={"gemini": fake_gemini, "ollama": fake_ollama},
        settings=settings,
        budget_manager=budget,
    )

    req = GenerationRequest[MockPlan](
        schema_type=MockPlan,
        prompt="Build site",
        role=AgentRole.BUILDER,
        run_id="run-fallback-test",
    )

    result = router.generate(req)

    assert result.data.step == "Fallback plan via Ollama"
    assert result.provider == "ollama"
    assert result.fallback_occurred is True
    assert "RateLimitError" in (result.fallback_reason or "")
    assert len(fake_gemini.calls) == 1
    assert len(fake_ollama.calls) == 1

    # Budget correctly records fallback call
    summary = budget.get_summary("run-fallback-test")
    assert summary.fallback_call_count == 1


def test_routing_llm_no_fallback_on_auth_failure() -> None:
    """Non-transient errors like AuthenticationError do NOT trigger fallback."""
    fake_gemini = FakeLLM(provider_name="gemini")
    fake_ollama = FakeLLM(provider_name="ollama")

    fake_gemini.set_failure(AuthenticationError("gemini", "API key expired"))
    fake_ollama.set_response(
        MockPlan, MockPlan(step="Should not be reached", priority=0)
    )

    settings = LLMSettings()
    router = RoutingLLM(
        providers={"gemini": fake_gemini, "ollama": fake_ollama},
        settings=settings,
    )

    req = GenerationRequest[MockPlan](
        schema_type=MockPlan,
        prompt="Design tokens",
        role=AgentRole.DESIGNER,
    )

    with pytest.raises(AuthenticationError):
        router.generate(req)

    assert len(fake_gemini.calls) == 1
    assert len(fake_ollama.calls) == 0


def test_routing_llm_no_fallback_on_schema_error() -> None:
    """Structured output errors do NOT trigger model fallback."""
    fake_gemini = FakeLLM(provider_name="gemini")
    fake_ollama = FakeLLM(provider_name="ollama")

    fake_gemini.set_failure(StructuredOutputError("MockPlan", "Malformed response"))
    settings = LLMSettings()
    router = RoutingLLM(
        providers={"gemini": fake_gemini, "ollama": fake_ollama},
        settings=settings,
    )

    req = GenerationRequest[MockPlan](
        schema_type=MockPlan,
        prompt="Review code",
        role=AgentRole.REVIEWER,
    )

    with pytest.raises(StructuredOutputError):
        router.generate(req)

    assert len(fake_gemini.calls) == 1
    assert len(fake_ollama.calls) == 0


def test_routing_llm_both_primary_and_fallback_fail() -> None:
    """Exhausting both primary and fallback raises FallbackExhaustedError."""
    fake_gemini = FakeLLM(provider_name="gemini")
    fake_ollama = FakeLLM(provider_name="ollama")

    fake_gemini.set_failure(ProviderUnavailableError("gemini", "503 Unavailable"))
    fake_ollama.set_failure(ProviderUnavailableError("ollama", "Connection refused"))

    settings = LLMSettings()
    router = RoutingLLM(
        providers={"gemini": fake_gemini, "ollama": fake_ollama},
        settings=settings,
    )

    req = GenerationRequest[MockPlan](
        schema_type=MockPlan,
        prompt="Summarize output",
        role=AgentRole.SUMMARIZER,
    )

    with pytest.raises(FallbackExhaustedError) as exc_info:
        router.generate(req)

    assert exc_info.value.primary_provider == "gemini"
    assert exc_info.value.fallback_provider == "ollama"


def test_routing_llm_token_budget_exhausted_blocks_call() -> None:
    """When token budget is exhausted, call is rejected before any LLM dispatch."""
    fake_gemini = FakeLLM(provider_name="gemini")
    budget = TokenBudgetManager(default_budget=500, default_reservation=1_000)

    settings = LLMSettings()
    router = RoutingLLM(
        providers={"gemini": fake_gemini},
        settings=settings,
        budget_manager=budget,
    )

    req = GenerationRequest[MockPlan](
        schema_type=MockPlan,
        prompt="Test budget",
        role=AgentRole.PM,
        run_id="run-budget-exhausted",
        max_output_tokens=1_000,
    )

    with pytest.raises(TokenBudgetExceededError):
        router.generate(req)

    # LLM was never contacted
    assert len(fake_gemini.calls) == 0


def test_routing_llm_generate_structured_convenience() -> None:
    """generate_structured method correctly delegates to generate and returns data."""
    fake_gemini = FakeLLM(provider_name="gemini")
    mock_plan = MockPlan(step="Quick step", priority=1)
    fake_gemini.set_response(MockPlan, mock_plan)

    settings = LLMSettings()
    router = RoutingLLM(providers={"gemini": fake_gemini}, settings=settings)

    data = router.generate_structured(
        schema=MockPlan,
        prompt="Quick plan",
        role="pm",
        run_id="run-structured-test",
    )

    assert data.step == "Quick step"
    assert data.priority == 1
