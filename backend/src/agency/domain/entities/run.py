"""Run aggregate root and state machine."""

import uuid
from datetime import UTC, datetime
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator

from agency.domain.entities.brief import Brief
from agency.domain.entities.spec import Spec
from agency.domain.enums import RunState
from agency.domain.errors import (
    ApprovalRequiredError,
    DomainInvariantError,
    InvalidApprovalError,
    InvalidRevisionRequestError,
    InvalidStateTransitionError,
    InvalidTerminalStateOperationError,
)
from agency.domain.events import (
    BuildCompleted,
    BuildStarted,
    DeploymentCompleted,
    DeploymentStarted,
    DomainEvent,
    PlanningCompleted,
    PrototypeApproved,
    PrototypeReady,
    QAFailed,
    QAPassed,
    RevisionRequested,
    RunCancelled,
    RunFailed,
    RunStarted,
)


class Run(BaseModel):
    """Central domain aggregate managing the multi-agent delivery lifecycle."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = Field(min_length=1, max_length=100)
    state: RunState = Field(default=RunState.CREATED)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    failure_reason: str | None = None
    cancellation_reason: str | None = None
    brief: Brief | None = None
    spec: Spec | None = None
    prototype_ref: str | None = None
    approval_recorded: bool = False
    approved_at: datetime | None = None
    approver: str | None = None
    revision_count: int = 0
    max_revisions: int = 3
    revision_history: list[str] = Field(default_factory=list)

    # In-memory pending domain event buffer
    _pending_events: list[DomainEvent] = PrivateAttr(default_factory=list)

    LEGAL_TRANSITIONS: ClassVar[dict[RunState, set[RunState]]] = {
        RunState.CREATED: {
            RunState.PLANNING,
            RunState.FAILED,
            RunState.CANCELLED,
        },
        RunState.PLANNING: {
            RunState.PROTOTYPING,
            RunState.FAILED,
            RunState.CANCELLED,
        },
        RunState.PROTOTYPING: {
            RunState.AWAITING_APPROVAL,
            RunState.FAILED,
            RunState.CANCELLED,
        },
        RunState.AWAITING_APPROVAL: {
            RunState.BUILDING,
            RunState.PROTOTYPING,  # Permitted on revision request
            RunState.FAILED,
            RunState.CANCELLED,
        },
        RunState.BUILDING: {
            RunState.TESTING,
            RunState.FAILED,
            RunState.CANCELLED,
        },
        RunState.TESTING: {
            RunState.DEPLOYING,
            RunState.FAILED,
            RunState.CANCELLED,
        },
        RunState.DEPLOYING: {
            RunState.COMPLETED,
            RunState.FAILED,
            RunState.CANCELLED,
        },
        RunState.COMPLETED: set(),
        RunState.FAILED: set(),
        RunState.CANCELLED: set(),
    }

    TERMINAL_STATES: ClassVar[set[RunState]] = {
        RunState.COMPLETED,
        RunState.FAILED,
        RunState.CANCELLED,
    }

    @field_validator("created_at", "updated_at", "approved_at")
    @classmethod
    def _validate_timezone_awareness(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Timestamps must be timezone-aware (UTC).")
        return value

    @field_validator("project_id", mode="before")
    @classmethod
    def _strip_project_id(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Project ID cannot be empty or whitespace.")
            return stripped
        return value

    # Event buffer management
    def collect_events(self) -> list[DomainEvent]:
        """Return an isolated copy of currently pending domain events."""
        return list(self._pending_events)

    def clear_events(self) -> list[DomainEvent]:
        """Drain and return all pending domain events."""
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    def _record_event(self, event: DomainEvent) -> None:
        self._pending_events.append(event)

    # Core state transition validation and execution
    def transition_to(
        self,
        target_state: RunState,
        at: datetime | None = None,
        failure_reason: str | None = None,
        cancellation_reason: str | None = None,
    ) -> None:
        """Enforce transition rules and update state."""
        if self.state in self.TERMINAL_STATES:
            raise InvalidTerminalStateOperationError(
                state=self.state,
                operation=f"transition to '{target_state.value}'",
            )

        if target_state not in self.LEGAL_TRANSITIONS[self.state]:
            raise InvalidStateTransitionError(
                from_state=self.state,
                to_state=target_state,
            )

        # Invariant: Approval required to enter BUILDING from AWAITING_APPROVAL
        if (
            self.state == RunState.AWAITING_APPROVAL
            and target_state == RunState.BUILDING
            and not self.approval_recorded
        ):
            raise ApprovalRequiredError(run_id=self.run_id, state=self.state)

        # Invariant: Failure transition requires reason
        if target_state == RunState.FAILED:
            reason = failure_reason or self.failure_reason
            if not reason or not reason.strip():
                raise DomainInvariantError(
                    "Failure transition requires a non-empty failure reason."
                )

        now = self._resolve_timestamp(at)
        from_state = self.state

        # Apply state changes atomically
        self.state = target_state
        self.updated_at = now

        if target_state == RunState.FAILED and failure_reason:
            self.failure_reason = failure_reason.strip()
        elif target_state == RunState.CANCELLED and cancellation_reason:
            self.cancellation_reason = cancellation_reason.strip()

        # Emit corresponding event if not handled by a higher-level domain method
        self._emit_lifecycle_event_for_transition(from_state, target_state, now)

    def _emit_lifecycle_event_for_transition(
        self, from_state: RunState, to_state: RunState, at: datetime
    ) -> None:
        if from_state == RunState.CREATED and to_state == RunState.PLANNING:
            self._record_event(
                RunStarted(
                    run_id=self.run_id,
                    project_id=self.project_id,
                    occurred_at=at,
                )
            )
        elif from_state == RunState.PLANNING and to_state == RunState.PROTOTYPING:
            self._record_event(
                PlanningCompleted(
                    run_id=self.run_id,
                    spec_id=self.spec.title if self.spec else None,
                    occurred_at=at,
                )
            )
        elif from_state == RunState.AWAITING_APPROVAL and to_state == RunState.BUILDING:
            self._record_event(
                BuildStarted(
                    run_id=self.run_id,
                    commit_sha=None,
                    occurred_at=at,
                )
            )
        elif from_state == RunState.BUILDING and to_state == RunState.TESTING:
            self._record_event(
                BuildCompleted(
                    run_id=self.run_id,
                    commit_sha="HEAD",
                    workspace_path=f"workspaces/{self.project_id}",
                    occurred_at=at,
                )
            )
        elif from_state == RunState.TESTING and to_state == RunState.DEPLOYING:
            self._record_event(
                DeploymentStarted(
                    run_id=self.run_id,
                    provider="default",
                    target_env="preview",
                    occurred_at=at,
                )
            )
        elif to_state == RunState.FAILED:
            self._record_event(
                RunFailed(
                    run_id=self.run_id,
                    from_state=from_state,
                    reason=self.failure_reason or "Unspecified failure",
                    occurred_at=at,
                )
            )
        elif to_state == RunState.CANCELLED:
            self._record_event(
                RunCancelled(
                    run_id=self.run_id,
                    from_state=from_state,
                    reason=self.cancellation_reason or "Cancelled by user",
                    occurred_at=at,
                )
            )

    # Domain workflow operations
    def start_planning(self, at: datetime | None = None) -> None:
        """Start the planning phase from CREATED state."""
        self.transition_to(RunState.PLANNING, at=at)

    def finish_planning(
        self, spec: Spec | None = None, at: datetime | None = None
    ) -> None:
        """Complete the planning phase with an optional Spec."""
        if spec is not None:
            self.spec = spec
        self.transition_to(RunState.PROTOTYPING, at=at)

    def submit_prototype(self, prototype_ref: str, at: datetime | None = None) -> None:
        """Submit a completed prototype and transition to AWAITING_APPROVAL."""
        if self.state != RunState.PROTOTYPING:
            raise InvalidStateTransitionError(
                from_state=self.state,
                to_state=RunState.AWAITING_APPROVAL,
                message=(
                    f"Cannot submit prototype from state '{self.state.value}'. "
                    "Must be in 'PROTOTYPING'."
                ),
            )
        stripped_ref = prototype_ref.strip()
        if not stripped_ref:
            raise DomainInvariantError(
                "Prototype reference cannot be empty or whitespace."
            )

        now = self._resolve_timestamp(at)
        self.prototype_ref = stripped_ref
        self.state = RunState.AWAITING_APPROVAL
        self.updated_at = now
        self._record_event(
            PrototypeReady(
                run_id=self.run_id,
                prototype_ref=self.prototype_ref,
                occurred_at=now,
            )
        )

    def approve_prototype(
        self,
        approver: str = "client",
        prototype_ref: str | None = None,
        at: datetime | None = None,
    ) -> None:
        """Record human approval for the prototype."""
        if self.state != RunState.AWAITING_APPROVAL:
            raise InvalidApprovalError(
                run_id=self.run_id,
                reason=(
                    f"Cannot approve prototype in state '{self.state.value}'. "
                    "Must be in 'AWAITING_APPROVAL'."
                ),
            )

        if self.approval_recorded:
            raise InvalidApprovalError(
                run_id=self.run_id,
                reason="Prototype has already been approved for this run.",
            )

        active_ref = prototype_ref or self.prototype_ref
        if not active_ref or not active_ref.strip():
            raise InvalidApprovalError(
                run_id=self.run_id,
                reason="Missing prototype reference. Cannot approve without prototype.",
            )

        stripped_approver = approver.strip()
        if not stripped_approver:
            raise InvalidApprovalError(
                run_id=self.run_id,
                reason="Approver identifier cannot be empty.",
            )

        now = self._resolve_timestamp(at)
        self.prototype_ref = active_ref.strip()
        self.approval_recorded = True
        self.approved_at = now
        self.approver = stripped_approver
        self.updated_at = now

        self._record_event(
            PrototypeApproved(
                run_id=self.run_id,
                prototype_ref=self.prototype_ref,
                approver=self.approver,
                occurred_at=now,
            )
        )

    def request_revision(self, reason: str, at: datetime | None = None) -> None:
        """Request revisions to the prototype, sending run back to PROTOTYPING."""
        if self.state != RunState.AWAITING_APPROVAL:
            raise InvalidRevisionRequestError(
                run_id=self.run_id,
                reason=(
                    f"Cannot request revision in state '{self.state.value}'. "
                    "Must be in 'AWAITING_APPROVAL'."
                ),
            )

        stripped_reason = reason.strip()
        if not stripped_reason:
            raise InvalidRevisionRequestError(
                run_id=self.run_id,
                reason="Revision reason cannot be empty or whitespace.",
            )

        if self.revision_count >= self.max_revisions:
            raise InvalidRevisionRequestError(
                run_id=self.run_id,
                reason=(
                    f"Revision limit exceeded. Maximum permitted revisions "
                    f"is {self.max_revisions}."
                ),
            )

        now = self._resolve_timestamp(at)
        self.revision_count += 1
        self.revision_history.append(stripped_reason)
        self.approval_recorded = False
        self.approved_at = None
        self.approver = None
        self.state = RunState.PROTOTYPING
        self.updated_at = now

        self._record_event(
            RevisionRequested(
                run_id=self.run_id,
                revision_number=self.revision_count,
                reason=stripped_reason,
                occurred_at=now,
            )
        )

    def reject_approval(self, reason: str, at: datetime | None = None) -> None:
        """Reject prototype approval permanently, transitioning to FAILED."""
        if self.state != RunState.AWAITING_APPROVAL:
            raise InvalidApprovalError(
                run_id=self.run_id,
                reason=(
                    f"Cannot reject approval in state '{self.state.value}'. "
                    "Must be in 'AWAITING_APPROVAL'."
                ),
            )
        stripped_reason = reason.strip()
        if not stripped_reason:
            raise DomainInvariantError(
                "Rejection reason cannot be empty or whitespace."
            )
        self.fail(reason=f"Prototype approval rejected: {stripped_reason}", at=at)

    def start_building(
        self, commit_sha: str | None = None, at: datetime | None = None
    ) -> None:
        """Begin building after prototype approval has been secured."""
        now = self._resolve_timestamp(at)
        self.transition_to(RunState.BUILDING, at=now)
        self._record_event(
            BuildStarted(
                run_id=self.run_id,
                commit_sha=commit_sha,
                occurred_at=now,
            )
        )

    def finish_building(
        self,
        commit_sha: str,
        workspace_path: str,
        at: datetime | None = None,
    ) -> None:
        """Complete build and transition to TESTING."""
        if not commit_sha.strip():
            raise DomainInvariantError("Commit SHA cannot be empty.")
        if not workspace_path.strip():
            raise DomainInvariantError("Workspace path cannot be empty.")

        now = self._resolve_timestamp(at)
        self.transition_to(RunState.TESTING, at=now)
        self._record_event(
            BuildCompleted(
                run_id=self.run_id,
                commit_sha=commit_sha.strip(),
                workspace_path=workspace_path.strip(),
                occurred_at=now,
            )
        )

    def pass_qa(self, total_checks: int = 1, at: datetime | None = None) -> None:
        """Record passed QA checks and transition to DEPLOYING."""
        if total_checks < 1:
            raise DomainInvariantError("Total passed QA checks must be at least 1.")
        now = self._resolve_timestamp(at)
        self._record_event(
            QAPassed(
                run_id=self.run_id,
                total_checks=total_checks,
                occurred_at=now,
            )
        )
        self.transition_to(RunState.DEPLOYING, at=now)

    def fail_qa(
        self,
        reason: str,
        failed_checks: list[str] | None = None,
        at: datetime | None = None,
    ) -> None:
        """Record failed QA checks and transition to FAILED."""
        stripped_reason = reason.strip()
        if not stripped_reason:
            raise DomainInvariantError(
                "QA failure reason cannot be empty or whitespace."
            )
        now = self._resolve_timestamp(at)
        self._record_event(
            QAFailed(
                run_id=self.run_id,
                failed_checks=failed_checks or [],
                reason=stripped_reason,
                occurred_at=now,
            )
        )
        self.fail(reason=f"QA checks failed: {stripped_reason}", at=now)

    def complete_deployment(
        self,
        url: str,
        provider: str = "vercel",
        is_production: bool = False,
        at: datetime | None = None,
    ) -> None:
        """Complete deployment and transition to terminal COMPLETED state."""
        stripped_url = url.strip()
        if not stripped_url:
            raise DomainInvariantError("Deployment URL cannot be empty or whitespace.")
        now = self._resolve_timestamp(at)
        self.transition_to(RunState.COMPLETED, at=now)
        self._record_event(
            DeploymentCompleted(
                run_id=self.run_id,
                provider=provider.strip(),
                url=stripped_url,
                is_production=is_production,
                occurred_at=now,
            )
        )

    def fail(self, reason: str, at: datetime | None = None) -> None:
        """Fail the run from any non-terminal state."""
        if self.state in self.TERMINAL_STATES:
            raise InvalidTerminalStateOperationError(
                state=self.state,
                operation="fail",
            )
        stripped = reason.strip()
        if not stripped:
            raise DomainInvariantError("Failure reason cannot be empty or whitespace.")
        self.transition_to(RunState.FAILED, at=at, failure_reason=stripped)

    def cancel(
        self, reason: str = "Cancelled by user", at: datetime | None = None
    ) -> None:
        """Cancel the run from any non-terminal state."""
        if self.state in self.TERMINAL_STATES:
            raise InvalidTerminalStateOperationError(
                state=self.state,
                operation="cancel",
            )
        stripped = reason.strip()
        if not stripped:
            raise DomainInvariantError(
                "Cancellation reason cannot be empty or whitespace."
            )
        self.transition_to(RunState.CANCELLED, at=at, cancellation_reason=stripped)

    @staticmethod
    def _resolve_timestamp(at: datetime | None) -> datetime:
        if at is not None:
            if at.tzinfo is None:
                raise ValueError("Specified timestamp must be timezone-aware (UTC).")
            return at
        return datetime.now(UTC)
