"""In-memory fake implementation of LLMPort for unit testing."""

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from agency.application.errors import LLMError
from agency.application.ports.llm import LLMPort
from agency.infrastructure.llm.errors import StructuredOutputError
from agency.infrastructure.llm.models import (
    AgentRole,
    GenerationRequest,
    GenerationResult,
    TokenUsage,
)

T = TypeVar("T", bound=BaseModel)


class FakeLLM(LLMPort):
    """Deterministic in-memory fake for structured LLM completions."""

    def __init__(
        self,
        provider_name: str = "fake",
        model_name: str = "fake-model",
        default_usage: TokenUsage | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.model_name = model_name
        self.default_usage = default_usage or TokenUsage.create(
            input_tokens=15, output_tokens=30
        )
        self._responses: dict[type[Any], Any] = {}
        self._sequences: list[Any] = []
        self._simulated_error: Exception | None = None
        self.calls: list[dict[str, Any]] = []

    def set_response(self, schema: type[T], response: T) -> None:
        """Configure a deterministic response for a target schema."""
        if not isinstance(response, schema):
            raise ValueError(
                f"Configured response '{response}' does not conform "
                f"to schema '{schema}'."
            )
        self._responses[schema] = response

    def set_sequence(self, sequence: list[Any]) -> None:
        """Configure an ordered sequence of responses or errors."""
        self._sequences = list(sequence)

    def set_failure(self, error: Exception | None) -> None:
        """Configure a simulated completion or provider failure."""
        self._simulated_error = error

    def clear(self) -> None:
        """Reset configured responses, recorded calls, sequences, and errors."""
        self._responses.clear()
        self._sequences.clear()
        self._simulated_error = None
        self.calls.clear()

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
        """Return pre-configured response conforming to requested schema."""
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
        """Execute deterministic generation returning a typed GenerationResult."""
        role_str = (
            request.role.value
            if isinstance(request.role, AgentRole)
            else str(request.role)
        )
        call_info: dict[str, Any] = {
            "schema": request.schema_type,
            "prompt": request.prompt,
            "role": role_str,
            "run_id": request.run_id,
            "correlation_id": request.correlation_id,
            "max_output_tokens": request.max_output_tokens,
            "timeout": request.timeout,
        }
        self.calls.append(call_info)

        if not request.prompt.strip():
            raise LLMError("Prompt cannot be empty.")
        if not role_str.strip():
            raise LLMError("Role cannot be empty.")

        if self._simulated_error:
            raise self._simulated_error

        # If a sequence item is configured
        if self._sequences:
            item = self._sequences.pop(0)
            if isinstance(item, Exception):
                raise item
            if isinstance(item, str):
                # Try validating raw JSON string against schema
                try:
                    parsed = request.schema_type.model_validate_json(item)
                    return GenerationResult[T](
                        data=parsed,
                        provider=self.provider_name,
                        model=self.model_name,
                        usage=self.default_usage,
                        correlation_id=request.correlation_id,
                    )
                except (ValidationError, ValueError) as exc:
                    raise StructuredOutputError(
                        request.schema_type.__name__,
                        f"Sequence raw text failed schema validation: {exc}",
                    ) from exc
            if isinstance(item, request.schema_type):
                return GenerationResult[T](
                    data=item.model_copy(deep=True),
                    provider=self.provider_name,
                    model=self.model_name,
                    usage=self.default_usage,
                    correlation_id=request.correlation_id,
                )

        name = request.schema_type.__name__
        response = self._responses.get(request.schema_type)
        if response is None:
            raise LLMError(f"No mock response configured for schema '{name}'.")

        if not isinstance(response, request.schema_type):
            raise LLMError(f"Mock response does not match expected schema '{name}'.")

        return GenerationResult[T](
            data=response.model_copy(deep=True),
            provider=self.provider_name,
            model=self.model_name,
            usage=self.default_usage,
            correlation_id=request.correlation_id,
        )
