"""Unit tests for OllamaAdapter for local inference and fallback."""

import json
from typing import Any

import pytest
from pydantic import BaseModel

from agency.infrastructure.llm.errors import (
    ModelTimeoutError,
    ProviderUnavailableError,
    StructuredOutputError,
)
from agency.infrastructure.llm.models import AgentRole, GenerationRequest
from agency.infrastructure.llm.ollama_adapter import OllamaAdapter
from agency.infrastructure.llm.retry_policy import RetryPolicy
from agency.infrastructure.llm.settings import LLMSettings


class MockOllamaSpec(BaseModel):
    name: str
    version: int


class MockOllamaTransport:
    """Mock transport for local Ollama HTTP requests."""

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
            raise RuntimeError("No mock response queued for Ollama transport.")
        resp = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(resp, Exception):
            raise resp
        return resp  # type: ignore[no-any-return]


def _make_ollama_body(
    content: str, prompt_eval: int = 12, eval_count: int = 24
) -> dict[str, Any]:
    return {
        "model": "llama3.1:8b",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "prompt_eval_count": prompt_eval,
        "eval_count": eval_count,
    }


def _dummy_retry_policy() -> RetryPolicy:
    return RetryPolicy(
        max_retries=2,
        initial_delay_seconds=0.01,
        sleep_fn=lambda _: None,
        jitter_fn=lambda _: 0.0,
    )


def test_ollama_adapter_successful_generation() -> None:
    """Successful structured JSON response from Ollama validates against schema."""
    settings = LLMSettings(ollama_base_url="http://localhost:11434")
    raw_json = json.dumps({"name": "Agency Project", "version": 1})
    transport = MockOllamaTransport([_make_ollama_body(raw_json, 14, 28)])

    adapter = OllamaAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockOllamaSpec](
        schema_type=MockOllamaSpec,
        prompt="Describe agency",
        role=AgentRole.PM,
    )

    result = adapter.generate(req)

    assert result.data.name == "Agency Project"
    assert result.data.version == 1
    assert result.provider == "ollama"
    assert result.usage.input_tokens == 14
    assert result.usage.output_tokens == 28
    assert result.usage.total_tokens == 42
    assert result.repair_attempts == 0
    assert len(transport.recorded_calls) == 1
    assert transport.recorded_calls[0]["url"] == "http://localhost:11434/api/chat"


def test_ollama_adapter_connection_failure() -> None:
    """Connection failure to local Ollama daemon raises ProviderUnavailableError."""
    settings = LLMSettings()
    transport = MockOllamaTransport(
        [
            ProviderUnavailableError(
                "ollama", "Connection refused: Ollama daemon not running"
            )
        ]
    )

    adapter = OllamaAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockOllamaSpec](
        schema_type=MockOllamaSpec,
        prompt="Describe agency",
        role=AgentRole.PM,
    )

    with pytest.raises(ProviderUnavailableError) as exc_info:
        adapter.generate(req)

    assert exc_info.value.provider == "ollama"


def test_ollama_adapter_schema_repair_flow() -> None:
    """Invalid schema triggers repair cycle with Ollama."""
    settings = LLMSettings()
    bad_json = json.dumps({"name": "Agency", "version": "not-a-number"})
    good_json = json.dumps({"name": "Agency", "version": 2})

    transport = MockOllamaTransport(
        [
            _make_ollama_body(bad_json, 10, 10),
            _make_ollama_body(good_json, 15, 15),
        ]
    )

    adapter = OllamaAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockOllamaSpec](
        schema_type=MockOllamaSpec,
        prompt="Generate spec",
        role=AgentRole.BUILDER,
    )

    res = adapter.generate(req)
    assert res.data.version == 2
    assert res.repair_attempts == 1
    assert res.usage.input_tokens == 25
    assert res.usage.output_tokens == 25
    assert res.usage.total_tokens == 50
    assert len(transport.recorded_calls) == 2


def test_ollama_adapter_timeout_handling() -> None:
    """Inference timeout raises ModelTimeoutError."""
    settings = LLMSettings()
    transport = MockOllamaTransport(
        [
            ModelTimeoutError("ollama", "llama3.1:8b", 30.0),
            ModelTimeoutError("ollama", "llama3.1:8b", 30.0),
            ModelTimeoutError("ollama", "llama3.1:8b", 30.0),
        ]
    )

    adapter = OllamaAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockOllamaSpec](
        schema_type=MockOllamaSpec,
        prompt="Review spec",
        role=AgentRole.REVIEWER,
    )

    with pytest.raises(ModelTimeoutError):
        adapter.generate(req)


def test_ollama_adapter_no_automatic_download_on_404() -> None:
    """Missing model on Ollama (HTTP 404) raises without automatic download."""
    settings = LLMSettings()
    transport = MockOllamaTransport(
        [
            ProviderUnavailableError(
                "ollama",
                "Model 'llama3.1:8b' not found (HTTP 404). "
                "Automatic download is disabled.",
            )
        ]
    )

    adapter = OllamaAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockOllamaSpec](
        schema_type=MockOllamaSpec,
        prompt="Summarize",
        role=AgentRole.SUMMARIZER,
    )

    with pytest.raises(ProviderUnavailableError) as exc_info:
        adapter.generate(req)

    assert "Automatic download is disabled" in str(exc_info.value)


def test_ollama_adapter_empty_response_handling() -> None:
    """Empty text output raises StructuredOutputError."""
    settings = LLMSettings()
    transport = MockOllamaTransport(
        [{"model": "llama3.1:8b", "message": {"content": ""}}]
    )

    adapter = OllamaAdapter(
        settings=settings,
        transport=transport,
        retry_policy=_dummy_retry_policy(),
    )

    req = GenerationRequest[MockOllamaSpec](
        schema_type=MockOllamaSpec,
        prompt="Summarize",
        role=AgentRole.SUMMARIZER,
        allow_repair=False,
    )

    with pytest.raises(StructuredOutputError):
        adapter.generate(req)
