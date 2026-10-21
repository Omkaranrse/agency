"""Cancellation models and invariants for workflow operations."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CancellationRequest(BaseModel):
    """Structured request to cancel an active workflow run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(
        default="Cancelled by user",
        min_length=1,
        max_length=500,
    )
    requested_by: str = Field(default="user", min_length=1, max_length=100)

    @field_validator("reason", "requested_by", mode="before")
    @classmethod
    def _strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("String fields cannot be empty or whitespace.")
            return stripped
        return value
