"""Typed domain-compatible models for structured LLM completions."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AgentRole(StrEnum):
    """Supported agent roles for structured generation tasks."""

    PM = "pm"
    DESIGNER = "designer"
    BUILDER = "builder"
    REVIEWER = "reviewer"
    SUMMARIZER = "summarizer"

    @classmethod
    def is_valid_role(cls, value: str) -> bool:
        """Check whether a given string is a valid agent role."""
        return value in cls._value2member_map_


class TokenUsage(BaseModel):
    """Detailed token accounting for an individual LLM generation call."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None

    @classmethod
    def create(
        cls, input_tokens: int | None = None, output_tokens: int | None = None
    ) -> "TokenUsage":
        """Compute total automatically when input and output counts are provided."""
        total = None
        if input_tokens is not None and output_tokens is not None:
            total = input_tokens + output_tokens
        return cls(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total,
        )


class GenerationRequest[T: BaseModel](BaseModel):
    """Structured generation request parameters."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    schema_type: type[T] = Field(description="Target Pydantic schema class.")
    prompt: str = Field(min_length=1, description="Context prompt instructions.")
    role: AgentRole | str = Field(description="Target agent role.")
    run_id: str = Field(default="default", min_length=1, max_length=100)
    correlation_id: str | None = Field(default=None, max_length=100)
    max_output_tokens: int | None = Field(default=None, gt=0, le=32_768)
    timeout: float | None = Field(default=None, gt=0.0, le=600.0)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    allow_repair: bool = Field(
        default=True, description="Whether schema repair retries are enabled."
    )


class GenerationResult[T: BaseModel](BaseModel):
    """Result of a structured LLM completion."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    data: T
    provider: str
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    repair_attempts: int = 0
    correlation_id: str | None = None
    fallback_occurred: bool = False
    fallback_reason: str | None = None

    @property
    def input_tokens(self) -> int | None:
        """Return input token count if recorded."""
        return self.usage.input_tokens

    @property
    def output_tokens(self) -> int | None:
        """Return output token count if recorded."""
        return self.usage.output_tokens

    @property
    def total_tokens(self) -> int | None:
        """Return total token count if recorded."""
        return self.usage.total_tokens


class TokenUsageSummary(BaseModel):
    """Aggregate token usage and budget status for a specific run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    budget_limit: int = 0
    remaining_tokens: int = 0
    call_count: int = 0
    repair_call_count: int = 0
    fallback_call_count: int = 0
