"""RequestRevision use case."""

from pydantic import BaseModel, ConfigDict, Field

from agency.application.errors import (
    EventPublicationError,
    InvalidRequestError,
    RevisionLimitExceededError,
    RunNotFoundError,
)
from agency.application.ports.event_bus import EventBusPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.domain.enums import RunState
from agency.domain.errors import InvalidRevisionRequestError


class RequestRevisionCommand(BaseModel):
    """Command input for requesting prototype revisions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)


class RequestRevisionResult(BaseModel):
    """Result output from requesting revisions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    state: RunState
    revision_count: int
    revision_history: list[str]


class RequestRevision:
    """Use case to request revisions to an awaiting prototype.

    Execution order:
    1. Retrieve aggregate by run ID.
    2. Validate revision input.
    3. Delegate revision rules, history recording, and transitions to Run.
    4. Persist the updated Run aggregate.
    5. Publish RevisionRequested domain event.
    """

    def __init__(
        self,
        repository: RunRepositoryPort,
        event_bus: EventBusPort,
    ) -> None:
        self._repository = repository
        self._event_bus = event_bus

    def execute(self, command: RequestRevisionCommand) -> RequestRevisionResult:
        """Execute the RequestRevision workflow."""
        run = self._repository.get_by_id(command.run_id)
        if run is None:
            raise RunNotFoundError(command.run_id)

        stripped_reason = command.reason.strip()
        if not stripped_reason:
            raise InvalidRequestError("Revision reason cannot be empty or whitespace.")

        # Delegate to domain aggregate
        try:
            run.request_revision(reason=stripped_reason)
        except InvalidRevisionRequestError as exc:
            if "Revision limit exceeded" in exc.message:
                raise RevisionLimitExceededError(
                    run_id=run.run_id, max_revisions=run.max_revisions
                ) from exc
            raise

        events = run.clear_events()

        # Persist updated aggregate
        self._repository.save(run)

        # Publish events
        try:
            self._event_bus.publish_all(events)
        except Exception as exc:
            raise EventPublicationError(
                f"Run '{run.run_id}' was persisted with revision, "
                f"but event publication failed: {exc}"
            ) from exc

        return RequestRevisionResult(
            run_id=run.run_id,
            state=run.state,
            revision_count=run.revision_count,
            revision_history=list(run.revision_history),
        )
