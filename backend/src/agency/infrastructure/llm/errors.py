"""Typed exception hierarchy for LLM infrastructure adapters and routing."""

from agency.application.errors import LLMError as LLMError


class LLMInfrastructureError(LLMError):
    """Base exception for all infrastructure-level LLM operations."""


class MissingAPIKeyError(LLMInfrastructureError):
    """Raised when a required provider API key is missing or blank."""

    def __init__(self, provider: str, env_var: str) -> None:
        self.provider = provider
        self.env_var = env_var
        super().__init__(
            f"API key for provider '{provider}' is missing. "
            f"Please set the '{env_var}' environment variable."
        )


class AuthenticationError(LLMInfrastructureError):
    """Raised when provider credentials, tokens, or permissions are rejected."""

    def __init__(self, provider: str, details: str = "Invalid credentials.") -> None:
        self.provider = provider
        super().__init__(f"Authentication failed for provider '{provider}': {details}")


class RateLimitError(LLMInfrastructureError):
    """Raised when an LLM provider rejects a request due to rate limiting (HTTP 429)."""

    def __init__(
        self,
        provider: str,
        message: str = "Rate limit exceeded.",
        retry_after: float | None = None,
    ) -> None:
        self.provider = provider
        self.retry_after = retry_after
        detail = f" (Retry-After: {retry_after}s)" if retry_after is not None else ""
        super().__init__(
            f"Rate limit exceeded for provider '{provider}': {message}{detail}"
        )


class ProviderUnavailableError(LLMInfrastructureError):
    """Raised when a provider is unreachable, offline, or returns 503."""

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"Provider '{provider}' is unavailable: {reason}")


class ModelTimeoutError(LLMInfrastructureError):
    """Raised when a generation request exceeds its bounded timeout."""

    def __init__(self, provider: str, model: str, timeout_seconds: float) -> None:
        self.provider = provider
        self.model = model
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Request to '{provider}' (model: '{model}') timed out after "
            f"{timeout_seconds:.1f} seconds."
        )


class InvalidRoleError(LLMInfrastructureError):
    """Raised when an unsupported agent role identifier is provided."""

    def __init__(self, role: str, supported_roles: list[str] | None = None) -> None:
        self.role = role
        self.supported_roles = supported_roles or [
            "pm",
            "designer",
            "builder",
            "reviewer",
            "summarizer",
        ]
        super().__init__(
            f"Unsupported agent role '{role}'. "
            f"Supported roles are: {', '.join(self.supported_roles)}."
        )


class StructuredOutputError(LLMInfrastructureError):
    """Raised when model response cannot be parsed or validated against schema."""

    def __init__(
        self,
        schema_name: str,
        message: str,
        repair_attempts: int = 0,
        validation_errors: list[str] | None = None,
    ) -> None:
        self.schema_name = schema_name
        self.repair_attempts = repair_attempts
        self.validation_errors = validation_errors or []
        super().__init__(
            f"Failed to generate structured data for schema '{schema_name}' "
            f"after {repair_attempts} repair attempt(s): {message}"
        )


class TokenBudgetExceededError(LLMInfrastructureError):
    """Raised when a generation request would exceed the per-run token budget."""

    def __init__(
        self,
        run_id: str,
        requested: int,
        remaining: int,
        budget: int = 0,
    ) -> None:
        self.run_id = run_id
        self.requested = requested
        self.remaining = remaining
        self.budget = budget
        super().__init__(
            f"Run '{run_id}' exceeded its token budget: requested {requested} tokens, "
            f"but only {remaining} of {budget} tokens remain."
        )

    @property
    def requested_tokens(self) -> int:
        return self.requested

    @property
    def remaining_tokens(self) -> int:
        return self.remaining


class FallbackExhaustedError(LLMInfrastructureError):
    """Raised when both primary and fallback providers fail to fulfill a request."""

    def __init__(
        self,
        primary_provider: str,
        fallback_provider: str,
        message: str = "",
        role: str = "unknown",
        primary_error: str = "",
        fallback_error: str = "",
    ) -> None:
        self.role = role
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.primary_error = primary_error
        self.fallback_error = fallback_error
        detail = (
            message
            or f"Primary ('{primary_provider}') failed: {primary_error}; "
            f"Fallback ('{fallback_provider}') failed: {fallback_error}."
        )
        super().__init__(f"All providers exhausted for role '{role}'. {detail}")
