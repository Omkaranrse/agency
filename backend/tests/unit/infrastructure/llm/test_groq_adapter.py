"""Unit tests for GroqAdapter with structured JSON generation and schema repairs."""

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
from agency.infrastructure.llm.groq_adapter import (
    GroqAdapter,
    _sanitize_error_text,
)
from agency.infrastructure.llm.models import AgentRole, GenerationRequest
from agency.infrastructure.llm.retry_policy import RetryPolicy
from agency.infrastructure.llm.routing_llm import RoutingLLM
from agency.infrastructure.llm.settings import LLMSettings


class MockSpec(BaseModel):
    title: str
    item_count: int


class MockGroqTransport:
    """Mock transport for Groq requests."""

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


def _make_groq_body(
    content: str, prompt_tokens: int = 15, completion_tokens: int = 25
) -> dict[str, Any]:
    return {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "llama-3.3-70b-versatile",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def test_missing_api_key_raises_error() -> None:
    settings = LLMSettings(groq_api_key=None)
    transport = MockGroqTransport([])
    adapter = GroqAdapter(settings=settings, transport=transport)
    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Generate",
        role=AgentRole.PM,
    )
    with pytest.raises(MissingAPIKeyError) as exc_info:
        adapter.generate(req)
    assert exc_info.value.provider == "groq"
    assert len(transport.recorded_calls) == 0


def test_successful_structured_generation() -> None:
    settings = LLMSettings.from_env(groq_api_key=SecretStr("gsk_mock_valid_key"))
    transport = MockGroqTransport(
        [_make_groq_body('{"title": "Groq App", "item_count": 5}')]
    )
    adapter = GroqAdapter(settings=settings, transport=transport)

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Design app",
        role=AgentRole.PM,
    )
    result = adapter.generate(req)

    assert result.data.title == "Groq App"
    assert result.data.item_count == 5
    assert result.provider == "groq"
    assert result.usage.total_tokens == 40
    assert len(transport.recorded_calls) == 1
    assert "Authorization" in transport.recorded_calls[0]["headers"]
    assert (
        "Bearer gsk_mock_valid_key"
        == transport.recorded_calls[0]["headers"]["Authorization"]
    )


def test_markdown_wrapped_json_parsed_successfully() -> None:
    settings = LLMSettings.from_env(groq_api_key=SecretStr("gsk_mock_valid_key"))
    markdown_content = '```json\n{"title": "Fenced App", "item_count": 3}\n```'
    transport = MockGroqTransport([_make_groq_body(markdown_content)])
    adapter = GroqAdapter(settings=settings, transport=transport)

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Design app",
        role=AgentRole.DESIGNER,
    )
    result = adapter.generate(req)
    assert result.data.title == "Fenced App"
    assert result.data.item_count == 3


def test_schema_repair_recovers_on_second_attempt() -> None:
    settings = LLMSettings.from_env(
        groq_api_key=SecretStr("gsk_mock_valid_key"),
        max_repair_retries=2,
    )
    transport = MockGroqTransport(
        [
            _make_groq_body('{"bad_key": 123}'),  # Fails schema validation
            _make_groq_body('{"title": "Repaired", "item_count": 7}'),  # Valid
        ]
    )
    adapter = GroqAdapter(settings=settings, transport=transport)

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Create spec",
        role=AgentRole.BUILDER,
        allow_repair=True,
    )
    result = adapter.generate(req)

    assert result.data.title == "Repaired"
    assert result.data.item_count == 7
    assert len(transport.recorded_calls) == 2


def test_exhausted_repairs_raises_structured_output_error() -> None:
    settings = LLMSettings.from_env(
        groq_api_key=SecretStr("gsk_mock_valid_key"),
        max_repair_retries=1,
    )
    transport = MockGroqTransport(
        [
            _make_groq_body('{"bad": 1}'),
            _make_groq_body('{"still_bad": 2}'),
        ]
    )
    adapter = GroqAdapter(settings=settings, transport=transport)

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Create spec",
        role=AgentRole.BUILDER,
        allow_repair=True,
    )
    with pytest.raises(StructuredOutputError):
        adapter.generate(req)


def test_rate_limit_error_handled() -> None:
    settings = LLMSettings.from_env(groq_api_key=SecretStr("gsk_mock_valid_key"))
    transport = MockGroqTransport(
        [RateLimitError("groq", "Rate limit hit", retry_after=5.0)]
    )
    retry_policy = RetryPolicy(max_retries=0)
    adapter = GroqAdapter(
        settings=settings, transport=transport, retry_policy=retry_policy
    )

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Test",
        role=AgentRole.PM,
    )
    with pytest.raises(RateLimitError) as exc_info:
        adapter.generate(req)
    assert exc_info.value.provider == "groq"
    assert exc_info.value.retry_after == 5.0


def test_authentication_error_handled() -> None:
    settings = LLMSettings.from_env(groq_api_key=SecretStr("gsk_invalid_key"))
    transport = MockGroqTransport(
        [AuthenticationError("groq", "HTTP 401: Unauthorized")]
    )
    retry_policy = RetryPolicy(max_retries=0)
    adapter = GroqAdapter(
        settings=settings, transport=transport, retry_policy=retry_policy
    )

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Test",
        role=AgentRole.PM,
    )
    with pytest.raises(AuthenticationError):
        adapter.generate(req)


def test_timeout_error_handled() -> None:
    settings = LLMSettings.from_env(groq_api_key=SecretStr("gsk_mock_valid_key"))
    transport = MockGroqTransport(
        [ModelTimeoutError("groq", "llama-3.3-70b-versatile", 30.0)]
    )
    retry_policy = RetryPolicy(max_retries=0)
    adapter = GroqAdapter(
        settings=settings, transport=transport, retry_policy=retry_policy
    )

    req = GenerationRequest[MockSpec](
        schema_type=MockSpec,
        prompt="Test",
        role=AgentRole.PM,
    )
    with pytest.raises(ModelTimeoutError):
        adapter.generate(req)


def test_secret_sanitization() -> None:
    raw = "Request failed with Authorization: Bearer gsk_secret_12345 in header."
    sanitized = _sanitize_error_text(raw)
    assert "gsk_secret_12345" not in sanitized
    assert "[REDACTED]" in sanitized


def test_routing_llm_routes_to_groq_when_configured() -> None:
    settings = LLMSettings(
        groq_api_key=SecretStr("gsk_mock_key"),
        primary_provider_by_role={
            AgentRole.PM.value: "groq",
            AgentRole.DESIGNER.value: "groq",
            AgentRole.BUILDER.value: "groq",
            AgentRole.REVIEWER.value: "groq",
            AgentRole.SUMMARIZER.value: "groq",
        },
    )
    transport = MockGroqTransport(
        [_make_groq_body('{"title": "Routed App", "item_count": 9}')]
    )
    groq_adapter = GroqAdapter(settings=settings, transport=transport)

    router = RoutingLLM(
        providers={"groq": groq_adapter},
        settings=settings,
    )
    res = router.generate_structured(MockSpec, "Prompt", AgentRole.PM.value)
    assert res.title == "Routed App"
    assert res.item_count == 9
