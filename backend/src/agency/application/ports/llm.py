"""LLMPort definition for structured AI completions."""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMPort(ABC):
    """Abstract port for structured language model completions.

    Provider-agnostic contract designed for deterministic schema generation.
    """

    @abstractmethod
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
        """Generate structured data conforming to the supplied Pydantic schema.

        Args:
            schema: The target Pydantic model class to validate and instantiate.
            prompt: Context and instructions for the generation request.
            role: The validated agent role identifier (e.g. 'pm', 'builder').
            run_id: Optional tracking identifier for the execution run.
            correlation_id: Optional correlation ID for tracing.
            max_output_tokens: Optional token generation budget limit for response.
            timeout: Optional maximum request timeout in seconds.

        Returns:
            A validated instance of the requested schema type T.

        Raises:
            LLMError: If generation fails, provider is unreachable, or
                the generated content cannot be validated against the schema.
        """

    def generate(self, request: Any) -> Any:
        """Execute a typed generation request and return full result metadata.

        Args:
            request: A GenerationRequest instance specifying schema, prompt, and role.

        Returns:
            A GenerationResult instance containing validated data and token usage.
        """
        raise NotImplementedError
