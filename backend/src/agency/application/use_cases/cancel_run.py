"""CancelRun use case."""

from pydantic import BaseModel, ConfigDict, Field

from agency.application.errors import (
    EventPublicationError,
    InvalidRequestError,
    RunNotFoundError,
)
from agency.application.ports.event_bus import EventBusPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.domain.enums import RunState


class CancelRunCommand(BaseModel):
    """Command input for cancelling an active Run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1)
    reason: str = Field(default="Cancelled by user", min_length=1, max_length=500)


class CancelRunResult(BaseModel):
    """Result output from cancelling a Run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    state: RunState
    cancellation_reason: str


class CancelRun:
    """Use case to cancel a non-terminal Run aggregate.

    Execution order:
    1. Retrieve aggregate by run ID.
    2. Validate cancellation input.
    3. Delegate cancellation to Run aggregate.
    4. Persist the updated Run aggregate.
    5. Publish emitted domain events (RunCancelled).
    """

    def __init__(
        self,
        repository: RunRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._repository = repository
        self._event_bus = event_bus

    def execute(self, command: CancelRunCommand) -> CancelRunResult:
        """Execute the CancelRun workflow."""
        run = self._repository.get_by_id(command.run_id)
        if run is None:
            raise RunNotFoundError(command.run_id)

        stripped_reason = command.reason.strip()
        if not stripped_reason:
            raise InvalidRequestError(
                "Cancellation reason cannot be empty or whitespace."
            )

        # Delegate cancellation invariants to domain aggregate
        run.cancel(reason=stripped_reason)
        events = run.clear_events()

        # Persist updated aggregate
        self._repository.save(run)

        # Publish events
        try:
            self._event_bus.publish_all(events)
        except Exception as exc:
            raise EventPublicationError(
                f"Run '{run.run_id}' was persisted as cancelled, "
                f"but event publication failed: {exc}"
            ) from exc

        assert run.cancellation_reason is not None

        return CancelRunResult(
            run_id=run.run_id,
            state=run.state,
            cancellation_reason=run.cancellation_reason,
        )
