"""Unit tests for structured output validation, schemas, and repair logic."""

import json
from enum import StrEnum
from typing import Any

import pytest
from pydantic import BaseModel, Field, SecretStr

from agency.infrastructure.llm.errors import StructuredOutputError
from agency.infrastructure.llm.gemini_adapter import GeminiAdapter
from agency.infrastructure.llm.models import AgentRole, GenerationRequest
from agency.infrastructure.llm.retry_policy import RetryPolicy
from agency.infrastructure.llm.settings import LLMSettings


class ComponentType(StrEnum):
    HEADER = "header"
    HERO = "hero"
    FOOTER = "footer"


class UIComponent(BaseModel):
    component_type: ComponentType
    props: dict[str, str] = Field(default_factory=dict)


class PageDesign(BaseModel):
    page_title: str
    components: list[UIComponent]


class SimpleMockTransport:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.recorded_requests: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        json_data: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        self.recorded_requests.append({"url": url, "json_data": json_data})
        if not self.responses:
            raise RuntimeError("No mock response queued.")
        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp  # type: ignore[no-any-return]


def _make_gemini_payload(
    text: str, in_tok: int = 20, out_tok: int = 40
) -> dict[str, Any]:
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": text}], "role": "model"},
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": in_tok,
            "candidatesTokenCount": out_tok,
        },
    }


def test_structured_output_nested_schema_validation() -> None:
    """Complex nested schema with Enums and Lists validates successfully."""
    settings = LLMSettings(gemini_api_key=SecretStr("mock-key"))
    valid_data = {
        "page_title": "Home Page",
        "components": [
            {"component_type": "header", "props": {"title": "My Agency"}},
            {"component_type": "hero", "props": {"tagline": "AI Engineering"}},
        ],
    }
    transport = SimpleMockTransport([_make_gemini_payload(json.dumps(valid_data))])
    adapter = GeminiAdapter(
        settings=settings,
        transport=transport,
        retry_policy=RetryPolicy(max_retries=0),
    )

    req = GenerationRequest[PageDesign](
        schema_type=PageDesign,
        prompt="Design home page",
        role=AgentRole.DESIGNER,
    )
    result = adapter.generate(req)

    assert result.data.page_title == "Home Page"
    assert len(result.data.components) == 2
    assert result.data.components[0].component_type == ComponentType.HEADER
    assert result.data.components[1].props["tagline"] == "AI Engineering"


def test_structured_output_repair_disabled_fails_immediately() -> None:
    """When allow_repair=False, validation failure raises with 0 repairs."""
    settings = LLMSettings(gemini_api_key=SecretStr("mock-key"))
    invalid_data = {
        "page_title": "Broken Page",
        "components": [{"component_type": "unknown_component", "props": {}}],
    }
    transport = SimpleMockTransport([_make_gemini_payload(json.dumps(invalid_data))])
    adapter = GeminiAdapter(
        settings=settings,
        transport=transport,
        retry_policy=RetryPolicy(max_retries=0),
    )

    req = GenerationRequest[PageDesign](
        schema_type=PageDesign,
        prompt="Design page",
        role=AgentRole.DESIGNER,
        allow_repair=False,
    )

    with pytest.raises(StructuredOutputError) as exc_info:
        adapter.generate(req)

    assert exc_info.value.repair_attempts == 0
    assert len(transport.recorded_requests) == 1


def test_structured_output_malformed_json_repaired() -> None:
    """Non-JSON text output is corrected during repair attempt."""
    settings = LLMSettings(gemini_api_key=SecretStr("mock-key"))
    # First attempt: raw non-json string
    bad_output = "Here is your JSON: ```json { invalid json ... } ```"
    good_output = json.dumps(
        {
            "page_title": "Repaired Page",
            "components": [],
        }
    )
    transport = SimpleMockTransport(
        [
            _make_gemini_payload(bad_output, 10, 15),
            _make_gemini_payload(good_output, 25, 30),
        ]
    )
    adapter = GeminiAdapter(
        settings=settings,
        transport=transport,
        retry_policy=RetryPolicy(max_retries=0),
    )

    req = GenerationRequest[PageDesign](
        schema_type=PageDesign,
        prompt="Design page",
        role=AgentRole.DESIGNER,
    )

    result = adapter.generate(req)
    assert result.data.page_title == "Repaired Page"
    assert result.repair_attempts == 1
    assert result.usage.input_tokens == 35  # 10 + 25
    assert result.usage.output_tokens == 45  # 15 + 30
    assert len(transport.recorded_requests) == 2

    # Check repair prompt contains repair attempt marker
    second_prompt = transport.recorded_requests[1]["json_data"]["contents"][0]["parts"][
        0
    ]["text"]
    assert "[SCHEMA REPAIR ATTEMPT 1/2]" in second_prompt
