"""Unit tests for token usage logging, safeguards, and credential redaction."""

import json
import logging
from collections.abc import Generator
from typing import Any

import pytest
from pydantic import BaseModel, SecretStr

from agency.infrastructure.llm.gemini_adapter import GeminiAdapter
from agency.infrastructure.llm.models import AgentRole, GenerationRequest
from agency.infrastructure.llm.ollama_adapter import OllamaAdapter
from agency.infrastructure.llm.retry_policy import RetryPolicy
from agency.infrastructure.llm.settings import LLMSettings


class LogSchema(BaseModel):
    message: str


class MockLogTransport:
    def __init__(self, response_body: dict[str, Any]) -> None:
        self.response_body = response_body

    def post(
        self,
        url: str,
        json_data: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        return self.response_body


class LogCaptureHandler(logging.Handler):
    """Custom logging handler to capture structured log records."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def log_capture() -> Generator[LogCaptureHandler, None, None]:
    logger = logging.getLogger("agency.infrastructure.llm.usage")
    logger.setLevel(logging.INFO)
    handler = LogCaptureHandler()
    logger.addHandler(handler)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)


def test_gemini_adapter_safe_usage_logging(log_capture: LogCaptureHandler) -> None:
    """Usage log contains metrics but redacts secret keys and full prompts."""
    secret_key = "super-secret-gemini-key-999"
    sensitive_prompt = (
        "Confidential client brief containing trade secrets: $100M revenue"
    )
    settings = LLMSettings(
        gemini_api_key=SecretStr(secret_key),
        log_usage_enabled=True,
    )

    resp_json = json.dumps({"message": "Generated public website"})
    resp_body = {
        "candidates": [
            {
                "content": {"parts": [{"text": resp_json}], "role": "model"},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 50,
            "candidatesTokenCount": 25,
            "totalTokenCount": 75,
        },
    }

    adapter = GeminiAdapter(
        settings=settings,
        transport=MockLogTransport(resp_body),
        retry_policy=RetryPolicy(max_retries=1, sleep_fn=lambda _: None),
    )

    req = GenerationRequest[LogSchema](
        schema_type=LogSchema,
        prompt=sensitive_prompt,
        role=AgentRole.PM,
        run_id="run-secure-123",
        correlation_id="corr-999",
    )

    adapter.generate(req)

    # Check that a log record was produced
    assert len(log_capture.records) >= 1
    record = log_capture.records[0]

    # Verification: secrets and full sensitive prompts never leaked
    log_text = record.getMessage()
    assert secret_key not in log_text
    assert sensitive_prompt not in log_text

    # Verification: structured metadata is safe and accurate
    extra = record.__dict__
    assert extra.get("run_id") == "run-secure-123"
    assert extra.get("correlation_id") == "corr-999"
    assert extra.get("provider") == "gemini"
    assert extra.get("input_tokens") == 50
    assert extra.get("output_tokens") == 25
    assert extra.get("total_tokens") == 75
    assert extra.get("status") == "success"

    # Ensure sensitive items are not in extra fields
    assert "prompt" not in extra
    assert "key" not in extra
    assert "secret" not in extra


def test_ollama_adapter_safe_usage_logging(log_capture: LogCaptureHandler) -> None:
    """Ollama adapter logs token metrics safely."""
    settings = LLMSettings(log_usage_enabled=True)
    resp_json = json.dumps({"message": "Local Ollama generation"})
    resp_body = {
        "model": "llama3.1:8b",
        "message": {"role": "assistant", "content": resp_json},
        "done": True,
        "prompt_eval_count": 30,
        "eval_count": 15,
    }

    adapter = OllamaAdapter(
        settings=settings,
        transport=MockLogTransport(resp_body),
        retry_policy=RetryPolicy(max_retries=1, sleep_fn=lambda _: None),
    )

    req = GenerationRequest[LogSchema](
        schema_type=LogSchema,
        prompt="Safe prompt",
        role=AgentRole.BUILDER,
        run_id="run-ollama-log",
    )

    adapter.generate(req)

    assert len(log_capture.records) >= 1
    record = log_capture.records[0]
    extra = record.__dict__
    assert extra.get("provider") == "ollama"
    assert extra.get("input_tokens") == 30
    assert extra.get("output_tokens") == 15
    assert extra.get("total_tokens") == 45
