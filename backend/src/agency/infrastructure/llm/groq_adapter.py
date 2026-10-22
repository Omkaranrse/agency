"""Groq LLM adapter supporting chat completions and structured JSON."""

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


class GroqTransport(Protocol):
    """Transport protocol for Groq REST requests, enabling mock injection."""

    def post(
        self,
        url: str,
        json_data: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        """Perform POST request and return decoded JSON response."""
        ...


class DefaultGroqTransport:
    """Production HTTP transport communicating with Groq REST API."""

    def __init__(self) -> None:
        self._session = requests.Session()

    def post(
        self,
        url: str,
        json_data: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        """Send HTTP POST using pooled session with bounded timeout and size."""
        try:
            resp = self._session.post(
                url, json=json_data, headers=headers, timeout=timeout
            )
        except requests.exceptions.Timeout as exc:
            raise ModelTimeoutError("groq", "unknown", timeout) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ProviderUnavailableError(
                "groq", f"Connection failed to Groq API: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderUnavailableError("groq", f"Network error: {exc}") from exc

        if len(resp.content) > MAX_RESPONSE_BYTES:
            raise StructuredOutputError(
                "unknown",
                f"Response size exceeded safety limit of {MAX_RESPONSE_BYTES} bytes.",
            )

        if resp.status_code in (401, 403):
            raise AuthenticationError(
                "groq",
                f"HTTP {resp.status_code}: {_sanitize_error_text(resp.text)}",
            )
        if resp.status_code == 429:
            retry_after: float | None = None
            if "Retry-After" in resp.headers:
                try:
                    retry_after = float(resp.headers["Retry-After"])
                except ValueError:
                    pass
            raise RateLimitError(
                "groq", _sanitize_error_text(resp.text), retry_after=retry_after
            )
        if resp.status_code >= 500:
            err_text = _sanitize_error_text(resp.text)
            raise ProviderUnavailableError(
                "groq",
                f"Server error HTTP {resp.status_code}: {err_text}",
            )
        if not resp.ok:
            raise ProviderUnavailableError(
                "groq",
                f"HTTP {resp.status_code}: {_sanitize_error_text(resp.text)}",
            )

        try:
            return resp.json()  # type: ignore[no-any-return]
        except Exception as exc:
            raise StructuredOutputError(
                "unknown", f"Failed to parse Groq JSON response: {exc}"
            ) from exc


def _sanitize_error_text(text: str) -> str:
    """Sanitize any API key or secret token patterns from error text."""
    sanitized = re.sub(r"gsk_[a-zA-Z0-9_]+", "[REDACTED]", text)
    sanitized = re.sub(
        r"(?i)\bbearer\s+[a-zA-Z0-9_\-\.]+", "Bearer [REDACTED]", sanitized
    )
    sanitized = re.sub(
        r"(?i)(api[-_]?key|token|secret|password|authorization)\s*[:=]\s*[^\s,]+",
        r"\1=[REDACTED]",
        sanitized,
    )
    return sanitized[:500]


class GroqAdapter(LLMPort):
    """Adapter for Groq inference implementing structured output generation."""

    def __init__(
        self,
        settings: LLMSettings | None = None,
        transport: GroqTransport | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.settings = settings or LLMSettings.from_env()
        self.transport = transport or DefaultGroqTransport()
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
            not self.settings.groq_api_key
            or not self.settings.groq_api_key.get_secret_value()
        ):
            raise MissingAPIKeyError("groq", "GROQ_API_KEY")

        role_str = (
            request.role.value
            if isinstance(request.role, AgentRole)
            else str(request.role)
        )
        model_name = self.settings.get_groq_model(role_str)
        max_tokens = request.max_output_tokens or self.settings.max_output_tokens
        timeout = request.timeout or self.settings.request_timeout_seconds

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

        schema_dict = request.schema_type.model_json_schema()
        system_instruction = (
            "You are a specialized AI system that outputs strictly valid JSON. "
            "You MUST output ONLY a valid JSON object adhering strictly to the "
            "following JSON Schema:\n"
            f"{json.dumps(schema_dict, indent=2)}\n"
            "Do not include any explanation or Markdown code blocks."
        )

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
            payload: dict[str, Any] = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": current_prompt},
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": max_tokens,
                "temperature": request.temperature,
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
            usage = resp_data.get("usage", {})
            total_input_tokens += int(usage.get("prompt_tokens", 0))
            total_output_tokens += int(usage.get("completion_tokens", 0))

            # Extract message content
            choices = resp_data.get("choices", [])
            if not choices:
                raise StructuredOutputError(
                    model_name, "Groq returned empty choices array in response."
                )

            content = choices[0].get("message", {}).get("content", "")
            if not content:
                raise StructuredOutputError(
                    model_name, "Groq returned empty text content in completion."
                )

            # Strip possible markdown code fence wrappers
            trimmed = content.strip()
            if trimmed.startswith("```"):
                lines = trimmed.splitlines()
                if len(lines) >= 3 and lines[0].startswith("```"):
                    trimmed = "\n".join(lines[1:-1]).strip()

            try:
                validated_data = request.schema_type.model_validate_json(trimmed)
                latency_ms = (time.monotonic() - start_time) * 1000

                usage_record = TokenUsage.create(
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )

                if self.settings.log_usage_enabled:
                    total_tok = usage_record.total_tokens or 0
                    usage_logger.info(
                        "LLM generation complete provider=groq model=%s role=%s "
                        "total_tokens=%d latency_ms=%.1f retries=%d repairs=%d",
                        model_name,
                        role_str,
                        total_tok,
                        latency_ms,
                        total_retries,
                        repair_attempts,
                    )

                return GenerationResult[T](
                    data=validated_data,
                    usage=usage_record,
                    provider="groq",
                    model=model_name,
                )

            except (ValidationError, json.JSONDecodeError) as exc:
                if repair_attempts < max_repairs:
                    repair_attempts += 1
                    err_msg = str(exc)[:300]
                    current_prompt = (
                        f"{request.prompt}\n\n"
                        f"CRITICAL: Your previous response was invalid. "
                        f"Error: {err_msg}\n"
                        f"Previous output:\n{trimmed[:500]}\n"
                        "Please correct the output to strictly conform to schema."
                    )
                    continue

                raise StructuredOutputError(
                    model_name,
                    f"Groq output validation failed after {repair_attempts} "
                    f"repair attempts: {exc}",
                ) from exc
