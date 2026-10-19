"""Ollama LLM adapter for local inference with structured output and repairs."""

import json
import logging
import re
import time
from typing import Any, Protocol, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from agency.application.ports.llm import LLMPort
from agency.infrastructure.llm.errors import (
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


class OllamaTransport(Protocol):
    """Transport protocol for Ollama REST requests, enabling mock injection."""

    def post(
        self,
        url: str,
        json_data: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        """Perform POST request and return decoded JSON response."""
        ...


class DefaultOllamaTransport:
    """Production HTTP transport communicating with local Ollama daemon."""

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
            raise ModelTimeoutError("ollama", "unknown", timeout) from exc
        except requests.exceptions.ConnectionError as exc:
            raise ProviderUnavailableError(
                "ollama", f"Connection failed to Ollama: {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderUnavailableError(
                "ollama", f"Network request error: {exc}"
            ) from exc

        if len(resp.content) > MAX_RESPONSE_BYTES:
            raise StructuredOutputError(
                "unknown",
                f"Response size exceeded safety limit of {MAX_RESPONSE_BYTES} bytes.",
            )

        if resp.status_code == 404:
            raise ProviderUnavailableError(
                "ollama",
                f"Model or endpoint not found (HTTP 404): {resp.text[:200]}. "
                "Automatic model downloads are disabled.",
            )
        if resp.status_code == 429:
            retry_after = None
            if "Retry-After" in resp.headers:
                try:
                    retry_after = float(resp.headers["Retry-After"])
                except ValueError:
                    pass
            raise RateLimitError("ollama", resp.text[:200], retry_after=retry_after)
        if resp.status_code >= 500:
            raise ProviderUnavailableError(
                "ollama", f"Server error HTTP {resp.status_code}: {resp.text[:200]}"
            )
        if not resp.ok:
            raise ProviderUnavailableError(
                "ollama", f"HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            return resp.json()  # type: ignore[no-any-return]
        except Exception as exc:
            raise StructuredOutputError(
                "unknown", f"Failed to parse Ollama JSON response: {exc}"
            ) from exc


def _sanitize_error_text(text: str) -> str:
    """Sanitize any API key or secret token patterns from error text."""
    sanitized = re.sub(
        r"(?i)(key|token|bearer|secret)\s*[:=]\s*[^\s]+", r"\1=[REDACTED]", text
    )
    return sanitized[:500]


class OllamaAdapter(LLMPort):
    """Adapter for local Ollama inference implementing structured output generation."""

    def __init__(
        self,
        settings: LLMSettings | None = None,
        transport: OllamaTransport | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.settings = settings or LLMSettings.from_env()
        self.transport = transport or DefaultOllamaTransport()
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
        """Execute structured generation via Ollama with retries and schema repair."""
        role_str = (
            request.role.value
            if isinstance(request.role, AgentRole)
            else str(request.role)
        )
        model_name = self.settings.get_ollama_model(role_str)
        max_tokens = request.max_output_tokens or self.settings.max_output_tokens
        timeout = request.timeout or self.settings.request_timeout_seconds

        base_url = self.settings.ollama_base_url.rstrip("/")
        url = f"{base_url}/api/chat"
        headers = {"Content-Type": "application/json"}

        total_input_tokens = 0
        total_output_tokens = 0
        repair_attempts = 0
        max_repairs = (
            min(self.settings.max_repair_retries, 2) if request.allow_repair else 0
        )
        current_prompt = request.prompt
        start_time = time.monotonic()
        total_retries = 0

        # We request json format with schema in format if supported, or "json" mode
        schema_dict = request.schema_type.model_json_schema()

        while True:
            payload: dict[str, Any] = {
                "model": model_name,
                "messages": [{"role": "user", "content": current_prompt}],
                "format": schema_dict,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
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

            # Extract token usage: Ollama provides prompt_eval_count and eval_count
            inp = resp_data.get("prompt_eval_count", 0)
            out = resp_data.get("eval_count", 0)
            total_input_tokens += inp
            total_output_tokens += out

            # Extract message content
            message = resp_data.get("message", {})
            raw_text = message.get("content", "")
            if not raw_text:
                # Ollama may return response in 'response' if /api/generate was used
                raw_text = resp_data.get("response", "")

            if not raw_text:
                raise StructuredOutputError(
                    request.schema_type.__name__,
                    "Ollama response contained no text output.",
                    repair_attempts=repair_attempts,
                )

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
                            "provider": "ollama",
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
                    provider="ollama",
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
