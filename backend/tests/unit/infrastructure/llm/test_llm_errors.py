"""Unit tests for typed LLM error hierarchy."""

from agency.application.errors import LLMError
from agency.infrastructure.llm.errors import (
    AuthenticationError,
    FallbackExhaustedError,
    InvalidRoleError,
    MissingAPIKeyError,
    ModelTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
    StructuredOutputError,
    TokenBudgetExceededError,
)


def test_llm_errors_inherit_from_base() -> None:
    """All domain-facing LLM infrastructure errors inherit from LLMError."""
    errs = [
        MissingAPIKeyError("gemini", "GEMINI_API_KEY"),
        AuthenticationError("gemini", "401 Unauthorized"),
        RateLimitError("gemini", "429 Too Many Requests", retry_after=12.0),
        ProviderUnavailableError("ollama", "Connection refused"),
        ModelTimeoutError("ollama", "llama3.1:8b", 30.0),
        InvalidRoleError("bad_role"),
        StructuredOutputError("MySchema", "Validation failed", repair_attempts=2),
        TokenBudgetExceededError("run-1", 5000, 2000),
        FallbackExhaustedError("gemini", "ollama", "Both failed"),
    ]

    for err in errs:
        assert isinstance(err, LLMError)
        assert isinstance(err, Exception)
        assert len(str(err)) > 0


def test_rate_limit_error_retry_after() -> None:
    """RateLimitError properly retains retry_after attribute."""
    err = RateLimitError("gemini", "Resource exhausted", retry_after=4.5)
    assert err.retry_after == 4.5
    assert err.provider == "gemini"


def test_structured_output_error_attributes() -> None:
    """StructuredOutputError maintains validation details and repair count."""
    err = StructuredOutputError(
        schema_name="DesignTokens",
        message="Missing field 'colors'",
        repair_attempts=2,
        validation_errors=["colors: Field required"],
    )
    assert err.schema_name == "DesignTokens"
    assert err.repair_attempts == 2
    assert len(err.validation_errors) == 1
