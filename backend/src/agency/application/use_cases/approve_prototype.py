"""ApprovePrototype use case."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from agency.application.errors import EventPublicationError, RunNotFoundError
from agency.application.ports.event_bus import EventBusPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.domain.enums import RunState


class ApprovePrototypeCommand(BaseModel):
    """Command input for recording human prototype approval."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1)
    approver: str = Field(default="client", min_length=1)
    prototype_ref: str | None = None


class ApprovePrototypeResult(BaseModel):
    """Result output from approving a prototype."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    state: RunState
    approved_at: datetime
    approver: str


class ApprovePrototype:
    """Use case to record human prototype approval and transition state.

    Execution order:
    1. Retrieve aggregate by run ID.
    2. Delegate approval invariants to Run aggregate.
    3. Persist the updated Run aggregate.
    4. Publish emitted domain events (PrototypeApproved).
    """

    def __init__(
        self,
        repository: RunRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._repository = repository
        self._event_bus = event_bus

    def execute(self, command: ApprovePrototypeCommand) -> ApprovePrototypeResult:
        """Execute the ApprovePrototype workflow."""
        run = self._repository.get_by_id(command.run_id)
        if run is None:
            raise RunNotFoundError(command.run_id)

        # Delegate validation and state transition to domain aggregate
        run.approve_prototype(
            approver=command.approver,
            prototype_ref=command.prototype_ref,
        )

        events = run.clear_events()

        # Persist updated aggregate
        self._repository.save(run)

        # Publish events
        try:
            self._event_bus.publish_all(events)
        except Exception as exc:
            raise EventPublicationError(
                f"Run '{run.run_id}' was persisted with approval, "
                f"but event publication failed: {exc}"
            ) from exc

        assert run.approved_at is not None
        assert run.approver is not None

        return ApprovePrototypeResult(
            run_id=run.run_id,
            state=run.state,
            approved_at=run.approved_at,
            approver=run.approver,
        )
