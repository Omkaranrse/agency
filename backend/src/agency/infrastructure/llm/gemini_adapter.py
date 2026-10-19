"""Gemini LLM adapter supporting structured JSON output, schema repairs, and retries."""

import json
import logging
import re
import time
from typing import Any, Protocol, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from agency.application.ports.llm import LLMPort
from agency.infrastructure.llm.errors import (
    AuthenticationError,
    MissingAPIKeyError,
    ModelTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
    StructuredOutputError,
)
from agency.infrastructure.llm.models import (
    AgentRole,
    GenerationRequest,
    GenerationResult,
    TokenUsage,
)
from agency.infrastructure.llm.retry_policy import RetryPolicy
from agency.infrastructure.llm.settings import LLMSettings

T = TypeVar("T", bound=BaseModel)
usage_logger = logging.getLogger("agency.infrastructure.llm.usage")

MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB safety limit


class GeminiTransport(Protocol):
    """Transport protocol for Gemini REST requests, enabling mock injection."""

    def post(
        self,
        url: str,
        json_data: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        """Perform POST request and return decoded JSON response."""
        ...


class DefaultGeminiTransport:
    """Production HTTP transport communicating with Google Generative Language API."""

    def post(
        self,
        url: str,
        json_data: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        """Send HTTP POST using requests with bounded timeout and size."""
        try:
            resp = requests.post(url, json=json_data, headers=headers, timeout=timeout)
        except requests.exceptions.Timeout as exc:
            raise ModelTimeoutError("gemini", "unknown", timeout) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ProviderUnavailableError(
                "gemini", f"Connection failed: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderUnavailableError(
                "gemini", f"Network request error: {exc}"
            ) from exc

        if len(resp.content) > MAX_RESPONSE_BYTES:
            raise StructuredOutputError(
                "unknown",
                f"Response size exceeded safety limit of {MAX_RESPONSE_BYTES} bytes.",
            )

        # Handle HTTP status codes
        if resp.status_code == 401 or resp.status_code == 403:
            raise AuthenticationError(
                "gemini", f"HTTP {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code == 429:
            retry_after = None
            if "Retry-After" in resp.headers:
                try:
                    retry_after = float(resp.headers["Retry-After"])
                except ValueError:
                    pass
            raise RateLimitError("gemini", resp.text[:200], retry_after=retry_after)
        if resp.status_code >= 500:
            raise ProviderUnavailableError(
                "gemini", f"Server error HTTP {resp.status_code}: {resp.text[:200]}"
            )
        if not resp.ok:
            raise ProviderUnavailableError(
                "gemini", f"HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            return resp.json()  # type: ignore[no-any-return]
        except Exception as exc:
            raise StructuredOutputError(
                "unknown", f"Failed to parse provider response: {exc}"
            ) from exc


def _sanitize_error_text(text: str) -> str:
    """Sanitize any API key or secret token patterns from error text."""
    sanitized = re.sub(
        r"(?i)(key|token|bearer|secret)\s*[:=]\s*[^\s]+", r"\1=[REDACTED]", text
    )
    return sanitized[:500]


class GeminiAdapter(LLMPort):
    """Adapter for Google Gemini LLMs implementing structured output generation."""

    def __init__(
        self,
        settings: LLMSettings | None = None,
        transport: GeminiTransport | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.settings = settings or LLMSettings.from_env()
        self.transport = transport or DefaultGeminiTransport()
        self.retry_policy = retry_policy or RetryPolicy(
            max_retries=self.settings.max_transient_retries,
            initial_delay_seconds=self.settings.initial_backoff_seconds,
            max_delay_seconds=self.settings.max_backoff_seconds,
            backoff_multiplier=self.settings.backoff_multiplier,
            overall_deadline_seconds=self.settings.overall_retry_deadline_seconds,
        )

    def generate_structured(
        self,
        schema: type[T],
        prompt: str,
        role: str,
        *,
        run_id: str | None = None,
        correlation_id: str | None = None,
        max_output_tokens: int | None = None,
        timeout: float | None = None,
    ) -> T:
        """Generate structured data conforming to target Pydantic schema."""
        req = GenerationRequest[T](
            schema_type=schema,
            prompt=prompt,
            role=role,
            run_id=run_id or "default",
            correlation_id=correlation_id,
            max_output_tokens=max_output_tokens,
            timeout=timeout,
        )
        res = self.generate(req)
        return res.data

    def generate(self, request: GenerationRequest[T]) -> GenerationResult[T]:
        """Execute structured generation with transient retries and schema repair."""
        if (
            not self.settings.gemini_api_key
            or not self.settings.gemini_api_key.get_secret_value()
        ):
            raise MissingAPIKeyError("gemini", "GEMINI_API_KEY")

        role_str = (
            request.role.value
            if isinstance(request.role, AgentRole)
            else str(request.role)
        )
        model_name = self.settings.get_gemini_model(role_str)
        max_tokens = request.max_output_tokens or self.settings.max_output_tokens
        timeout = request.timeout or self.settings.request_timeout_seconds

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}"
            f":generateContent?key={self.settings.gemini_api_key.get_secret_value()}"
        )
        headers = {"Content-Type": "application/json"}

        # Schema definition for JSON response mode
        schema_dict = request.schema_type.model_json_schema()

        total_input_tokens = 0
        total_output_tokens = 0
        repair_attempts = 0
        max_repairs = (
            min(self.settings.max_repair_retries, 2) if request.allow_repair else 0
        )
        current_prompt = request.prompt
        start_time = time.monotonic()
        total_retries = 0

        while True:
            payload = {
                "contents": [{"parts": [{"text": current_prompt}]}],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "response_schema": schema_dict,
                    "max_output_tokens": max_tokens,
                    "temperature": request.temperature,
                },
            }

            def _call(p: dict[str, Any] = payload) -> dict[str, Any]:
                return self.transport.post(
                    url=url,
                    json_data=p,
                    headers=headers,
                    timeout=timeout,
                )

            resp_data, call_retries = self.retry_policy.execute(_call)
            total_retries += call_retries

            # Extract token usage
            usage_meta = resp_data.get("usageMetadata", {})
            inp = usage_meta.get("promptTokenCount", 0)
            out = usage_meta.get("candidatesTokenCount", 0)
            total_input_tokens += inp
            total_output_tokens += out

            # Extract generated content text
            candidates = resp_data.get("candidates", [])
            if not candidates:
                raise StructuredOutputError(
                    request.schema_type.__name__,
                    "Model response contained no candidate outputs.",
                    repair_attempts=repair_attempts,
                )

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise StructuredOutputError(
                    request.schema_type.__name__,
                    "Candidate response contained no text parts.",
                    repair_attempts=repair_attempts,
                )

            raw_text = parts[0].get("text", "")

            # Validate against Pydantic schema
            try:
                validated_model = request.schema_type.model_validate_json(raw_text)
                duration_ms = int((time.monotonic() - start_time) * 1000)

                usage = TokenUsage.create(
                    input_tokens=total_input_tokens or None,
                    output_tokens=total_output_tokens or None,
                )

                if self.settings.log_usage_enabled:
                    usage_logger.info(
                        "LLM call completed successfully",
                        extra={
                            "run_id": request.run_id,
                            "correlation_id": request.correlation_id,
                            "agent_role": role_str,
                            "provider": "gemini",
                            "model": model_name,
                            "input_tokens": usage.input_tokens,
                            "output_tokens": usage.output_tokens,
                            "total_tokens": usage.total_tokens,
                            "duration_ms": duration_ms,
                            "retry_count": total_retries,
                            "repair_count": repair_attempts,
                            "status": "success",
                            "fallback_occurred": False,
                        },
                    )

                return GenerationResult[T](
                    data=validated_model,
                    provider="gemini",
                    model=model_name,
                    usage=usage,
                    repair_attempts=repair_attempts,
                    correlation_id=request.correlation_id,
                )

            except (ValidationError, json.JSONDecodeError, ValueError) as val_err:
                if repair_attempts >= max_repairs:
                    err_msg = _sanitize_error_text(str(val_err))
                    raise StructuredOutputError(
                        schema_name=request.schema_type.__name__,
                        message=f"Schema validation failed: {err_msg}",
                        repair_attempts=repair_attempts,
                        validation_errors=[err_msg],
                    ) from val_err

                repair_attempts += 1
                sanitized_feedback = _sanitize_error_text(str(val_err))
                name = request.schema_type.__name__
                current_prompt = (
                    f"{request.prompt}\n\n"
                    f"[SCHEMA REPAIR ATTEMPT {repair_attempts}/{max_repairs}]\n"
                    f"Previous output failed validation for {name}.\n"
                    f"Validation errors:\n{sanitized_feedback}\n"
                    f"Please output ONLY valid JSON matching the schema."
                )
