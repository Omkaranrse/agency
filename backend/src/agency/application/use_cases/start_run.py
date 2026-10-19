"""StartRun use case."""

import uuid
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from agency.application.errors import EventPublicationError, InvalidRequestError
from agency.application.ports.event_bus import EventBusPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.domain.entities.brief import Brief
from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.domain.events import RunStarted


class StartRunCommand(BaseModel):
    """Command input for initiating a new agency Run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str = Field(min_length=1, max_length=100)
    brief: Brief
    run_id: str | None = Field(default=None, max_length=100)


class StartRunResult(BaseModel):
    """Result output from starting an agency Run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    project_id: str
    state: RunState


class StartRun:
    """Use case to create and persist a new Run aggregate from a client brief.

    Execution order:
    1. Validate input command.
    2. Instantiate the Run aggregate in CREATED state.
    3. Persist the aggregate through RunRepositoryPort.
    4. Publish the RunStarted event through EventBusPort.

    Consistency policy:
    Persistence precedes event publication. If repository persistence fails,
    events are never published and the operation is aborted. If event
    publication fails following successful persistence, the truthful persisted
    state is maintained and an EventPublicationError is raised.
    """

    def __init__(
        self,
        repository: RunRepositoryPort,
        event_bus: EventBusPort,
        run_id_generator: Callable[[], str] | None = None,
    ) -> None:
        self._repository = repository
        self._event_bus = event_bus
        self._run_id_generator = run_id_generator or (lambda: str(uuid.uuid4()))

    def execute(self, command: StartRunCommand) -> StartRunResult:
        """Execute the StartRun workflow."""
        stripped_project_id = command.project_id.strip()
        if not stripped_project_id:
            raise InvalidRequestError("Project ID cannot be empty or whitespace.")

        run_id = command.run_id or self._run_id_generator()
        stripped_run_id = run_id.strip()
        if not stripped_run_id:
            raise InvalidRequestError("Run ID cannot be empty or whitespace.")

        # 1. Create aggregate in initial CREATED state
        run = Run(
            run_id=stripped_run_id,
            project_id=stripped_project_id,
            brief=command.brief,
            state=RunState.CREATED,
        )

        # 2. Persist aggregate to repository
        self._repository.save(run)

        # 3. Publish initial lifecycle event
        events = [
            RunStarted(run_id=run.run_id, project_id=run.project_id)
        ] + run.clear_events()

        try:
            self._event_bus.publish_all(events)
        except Exception as exc:
            raise EventPublicationError(
                f"Run '{run.run_id}' was persisted, but event publication failed: {exc}"
            ) from exc

        return StartRunResult(
            run_id=run.run_id,
            project_id=run.project_id,
            state=run.state,
        )
