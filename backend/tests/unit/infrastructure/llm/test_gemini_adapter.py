"""Unit tests for GeminiAdapter with structured JSON generation and schema repairs."""

import json
from typing import Any

import pytest
from pydantic import BaseModel, SecretStr

from agency.infrastructure.llm.errors import (
    AuthenticationError,
    MissingAPIKeyError,
    ModelTimeoutError,
    RateLimitError,
    StructuredOutputError,
)
from agency.infrastructure.llm.gemini_adapter import GeminiAdapter, _sanitize_error_text
from agency.infrastructure.llm.models import AgentRole, GenerationRequest
from agency.infrastructure.llm.retry_policy import RetryPolicy
from agency.infrastructure.llm.settings import LLMSettings


class MockSpec(BaseModel):
    title: str
    item_count: int


class MockGeminiTransport:
    """Mock transport for Gemini requests."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.recorded_calls: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        json_data: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        self.recorded_calls.append(
            {
                "url": url,
                "json_data": json_data,
                "headers": headers,
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise RuntimeError("No mock response queued.")
        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp  # type: ignore[no-any-return]


def _make_gemini_body(
    text: str, prompt_tokens: int = 10, candidates_tokens: int = 20
) -> dict[str, Any]:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": prompt_tokens,
            "candidatesTokenCount": candidates_tokens,
            "totalTokenCount": prompt_tokens + candidates_tokens,
        },
    }


def _dummy_retry_policy() -> RetryPolicy:
    return RetryPolicy(
        max_retries=2,
        initial_delay_seconds=0.01,
        sleep_fn=lambda _: None,
        jitter_fn=lambda _: 0.0,
    )


def test_gemini_adapter_missing_api_key() -> None:
    """Missing API key raises MissingAPIKeyError before sending request."""
    settings = LLMSettings(gemini_api_key=None)
    adapter = GeminiAdapter(settings=settings)

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Create a spec",
        role=AgentRole.PM,
    )
    with pytest.raises(MissingAPIKeyError) as exc_info:
        adapter.generate(req)

    assert exc_info.value.provider == "gemini"


def test_gemini_adapter_successful_generation() -> None:
    """Successful structured JSON response validates against target schema."""
    settings = LLMSettings(gemini_api_key=SecretStr("mock-key-123"))
    raw_json = json.dumps({"title": "Agency App", "item_count": 5})
    transport = MockGeminiTransport([_make_gemini_body(raw_json, 15, 25)])

    adapter = GeminiAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Design app structure",
        role=AgentRole.DESIGNER,
    )
    result = adapter.generate(req)

    assert result.data.title == "Agency App"
    assert result.data.item_count == 5
    assert result.provider == "gemini"
    assert result.model == settings.get_gemini_model("designer")
    assert result.usage.input_tokens == 15
    assert result.usage.output_tokens == 25
    assert result.usage.total_tokens == 40
    assert result.repair_attempts == 0
    assert len(transport.recorded_calls) == 1


def test_gemini_adapter_schema_repair_success() -> None:
    """Invalid schema output triggers schema repair and succeeds on retry."""
    settings = LLMSettings(gemini_api_key=SecretStr("mock-key-123"))
    # First response fails: item_count is string instead of int
    bad_json = json.dumps({"title": "Bad Spec", "item_count": "not_an_int"})
    good_json = json.dumps({"title": "Repaired Spec", "item_count": 10})

    transport = MockGeminiTransport(
        [
            _make_gemini_body(bad_json, 10, 15),
            _make_gemini_body(good_json, 20, 25),
        ]
    )

    adapter = GeminiAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Build spec",
        role=AgentRole.BUILDER,
    )
    result = adapter.generate(req)

    assert result.data.title == "Repaired Spec"
    assert result.data.item_count == 10
    assert result.repair_attempts == 1
    # Usage aggregated across attempts: (10 + 20) = 30 input, (15 + 25) = 40 output
    assert result.usage.input_tokens == 30
    assert result.usage.output_tokens == 40
    assert result.usage.total_tokens == 70
    assert len(transport.recorded_calls) == 2


def test_gemini_adapter_schema_repair_exhausted() -> None:
    """Exhausting maximum two repair retries raises StructuredOutputError."""
    settings = LLMSettings(gemini_api_key=SecretStr("mock-key-123"))
    bad_json = json.dumps({"invalid": True})

    transport = MockGeminiTransport(
        [
            _make_gemini_body(bad_json, 10, 10),
            _make_gemini_body(bad_json, 10, 10),
            _make_gemini_body(bad_json, 10, 10),
        ]
    )

    adapter = GeminiAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Build spec",
        role=AgentRole.BUILDER,
    )

    with pytest.raises(StructuredOutputError) as exc_info:
        adapter.generate(req)

    assert exc_info.value.schema_name == "MockSpec"
    assert exc_info.value.repair_attempts == 2
    assert len(transport.recorded_calls) == 3


def test_gemini_adapter_authentication_failure() -> None:
    """Authentication errors are not retried and raise immediately."""
    settings = LLMSettings(gemini_api_key=SecretStr("invalid-key"))
    transport = MockGeminiTransport([AuthenticationError("gemini", "API_KEY_INVALID")])

    adapter = GeminiAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Summarize",
        role=AgentRole.SUMMARIZER,
    )

    with pytest.raises(AuthenticationError):
        adapter.generate(req)

    assert len(transport.recorded_calls) == 1


def test_gemini_adapter_rate_limit_retry() -> None:
    """Rate limit transient error is retried and succeeds."""
    settings = LLMSettings(gemini_api_key=SecretStr("mock-key-123"))
    good_json = json.dumps({"title": "Rate Limit Recovered", "item_count": 2})

    transport = MockGeminiTransport(
        [
            RateLimitError("gemini", "Resource exhausted", retry_after=0.01),
            _make_gemini_body(good_json, 10, 20),
        ]
    )

    adapter = GeminiAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Review output",
        role=AgentRole.REVIEWER,
    )
    res = adapter.generate(req)
    assert res.data.title == "Rate Limit Recovered"
    assert len(transport.recorded_calls) == 2


def test_gemini_adapter_timeout_error() -> None:
    """Request timeout raises ModelTimeoutError."""
    settings = LLMSettings(gemini_api_key=SecretStr("mock-key-123"))
    transport = MockGeminiTransport(
        [
            ModelTimeoutError("gemini", "gemini-1.5-flash", 5.0),
            ModelTimeoutError("gemini", "gemini-1.5-flash", 5.0),
            ModelTimeoutError("gemini", "gemini-1.5-flash", 5.0),
        ]
    )

    adapter = GeminiAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Review output",
        role=AgentRole.REVIEWER,
    )

    with pytest.raises(ModelTimeoutError):
        adapter.generate(req)


def test_sanitize_error_text_redacts_credentials() -> None:
    """Sanitizer scrubs API keys, bearer tokens, and secrets from error feedback."""
    raw = "Failed with key=AIzaSyD-12345secret and token: bearer-xyz-987"
    sanitized = _sanitize_error_text(raw)
    assert "AIzaSyD" not in sanitized
    assert "bearer-xyz" not in sanitized
    assert "[REDACTED]" in sanitized
