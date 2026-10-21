"""Request and response DTO schemas for human approval, revision, and cancellation."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ApproveRunRequest(BaseModel):
    """Payload to authorize production build and deployment for the current preview."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    revision: int = Field(ge=0, description="Preview revision being approved")
    approver: str = Field(default="client", min_length=1, max_length=100)
    idempotency_key: str | None = Field(default=None, max_length=100)


class ApproveRunResponse(BaseModel):
    """Result returned after approval is successfully accepted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    status: str
    decision: str = "approved"
    revision: int
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReviseRunRequest(BaseModel):
    """Payload to reject current preview and request targeted modifications."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    revision: int = Field(ge=0, description="Current preview revision to revise")
    comment: str = Field(
        min_length=1,
        max_length=1000,
        description="Mandatory actionable feedback for revision",
    )
    idempotency_key: str | None = Field(default=None, max_length=100)


class ReviseRunResponse(BaseModel):
    """Result returned after revision request is accepted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    status: str
    decision: str = "revised"
    new_revision: int
    comment: str
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CancelRunRequest(BaseModel):
    """Payload to explicitly abort an active workflow run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    reason: str = Field(default="Cancelled by user", min_length=1, max_length=500)


class CancelRunResponse(BaseModel):
    """Result returned after cancellation is recorded."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    status: str
    reason: str
    cancelled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
