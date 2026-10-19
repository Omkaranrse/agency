"""Domain events for the Agency multi-agent delivery workflow."""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agency.domain.enums import RunState


class DomainEvent(BaseModel):
    """Immutable base class for all domain events."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("occurred_at")
    @classmethod
    def _validate_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware (UTC).")
        return value


class RunStarted(DomainEvent):
    """Emitted when a run begins its execution workflow."""

    project_id: str


class PlanningCompleted(DomainEvent):
    """Emitted when specification and planning phase finishes."""

    spec_id: str | None = None


class PrototypeReady(DomainEvent):
    """Emitted when a prototype has been generated and is ready for client review."""

    prototype_ref: str


class PrototypeApproved(DomainEvent):
    """Emitted when human approval is explicitly granted for a prototype."""

    prototype_ref: str
    approver: str


class RevisionRequested(DomainEvent):
    """Emitted when human review requests revisions to the prototype."""

    revision_number: int
    reason: str


class BuildStarted(DomainEvent):
    """Emitted when code generation and compilation build begins."""

    commit_sha: str | None = None


class BuildCompleted(DomainEvent):
    """Emitted when code build successfully finishes."""

    commit_sha: str
    workspace_path: str


class QAPassed(DomainEvent):
    """Emitted when automated QA checks successfully pass."""

    total_checks: int


class QAFailed(DomainEvent):
    """Emitted when automated QA checks fail."""

    failed_checks: list[str]
    reason: str


class DeploymentStarted(DomainEvent):
    """Emitted when preview or production deployment starts."""

    provider: str
    target_env: str


class DeploymentCompleted(DomainEvent):
    """Emitted when deployment succeeds with an accessible URL."""

    provider: str
    url: str
    is_production: bool


class RunFailed(DomainEvent):
    """Emitted when a run transitions to the terminal FAILED state."""

    from_state: RunState
    reason: str


class RunCancelled(DomainEvent):
    """Emitted when a run is cancelled from a nonterminal state."""

    from_state: RunState
    reason: str
