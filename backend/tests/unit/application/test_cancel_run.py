"""Unit tests for CancelRun use case."""

import pytest
from pydantic import ValidationError
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_run_repository import FakeRunRepository

from agency.application.errors import (
    EventPublicationError,
    InvalidRequestError,
    RepositoryError,
    RunNotFoundError,
)
from agency.application.use_cases.cancel_run import (
    CancelRun,
    CancelRunCommand,
)
from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.domain.errors import InvalidTerminalStateOperationError
from agency.domain.events import RunCancelled


@pytest.fixture
def fake_repo() -> FakeRunRepository:
    """Provide a fresh in-memory repository."""
    return FakeRunRepository()


@pytest.fixture
def fake_bus() -> FakeEventBus:
    """Provide a fresh in-memory event bus."""
    return FakeEventBus()


@pytest.mark.parametrize(
    "initial_setup",
    [
        lambda r: None,  # CREATED
        lambda r: r.start_planning(),  # PLANNING
        lambda r: (r.start_planning(), r.finish_planning()),  # PROTOTYPING
        lambda r: (
            r.start_planning(),
            r.finish_planning(),
            r.submit_prototype("p1"),
        ),  # AWAITING_APPROVAL
        lambda r: (
            r.start_planning(),
            r.finish_planning(),
            r.submit_prototype("p1"),
            r.approve_prototype("client"),
            r.start_building(),
        ),  # BUILDING
        lambda r: (
            r.start_planning(),
            r.finish_planning(),
            r.submit_prototype("p1"),
            r.approve_prototype("client"),
            r.start_building(),
            r.finish_building("sha1", "workspace/p1"),
        ),  # TESTING
        lambda r: (
            r.start_planning(),
            r.finish_planning(),
            r.submit_prototype("p1"),
            r.approve_prototype("client"),
            r.start_building(),
            r.finish_building("sha1", "workspace/p1"),
            r.pass_qa(),
        ),  # DEPLOYING
    ],
)
def test_cancel_run_success_from_non_terminal_states(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    initial_setup: object,
) -> None:
    """Test successful cancellation from any non-terminal state."""
    run = Run(run_id="run-cancel-test", project_id="proj-cancel")
    if callable(initial_setup):
        initial_setup(run)
    run.clear_events()
    fake_repo.save(run)

    use_case = CancelRun(repository=fake_repo, event_bus=fake_bus)
    command = CancelRunCommand(
        run_id=run.run_id,
        reason="Client requested project halt.",
    )

    result = use_case.execute(command)

    assert result.run_id == run.run_id
    assert result.state == RunState.CANCELLED
    assert result.cancellation_reason == "Client requested project halt."

    # Verify repository persistence
    saved_run = fake_repo.get_by_id(run.run_id)
    assert saved_run is not None
    assert saved_run.state == RunState.CANCELLED
    assert saved_run.cancellation_reason == "Client requested project halt."

    # Verify event publication
    assert len(fake_bus.events) == 1
    event = fake_bus.events[0]
    assert isinstance(event, RunCancelled)
    assert event.run_id == run.run_id
    assert event.reason == "Client requested project halt."


def test_cancel_run_missing_run_raises_not_found(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test cancelling non-existent run raises RunNotFoundError."""
    use_case = CancelRun(repository=fake_repo, event_bus=fake_bus)
    command = CancelRunCommand(run_id="non-existent")

    with pytest.raises(RunNotFoundError, match="Run 'non-existent' was not found"):
        use_case.execute(command)


def test_cancel_run_empty_reason_rejected(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that empty or whitespace cancellation reason is rejected."""
    run = Run(run_id="run-c1", project_id="proj-1")
    fake_repo.save(run)

    use_case = CancelRun(repository=fake_repo, event_bus=fake_bus)

    with pytest.raises(ValidationError):
        CancelRunCommand(run_id=run.run_id, reason="")

    command = CancelRunCommand(run_id=run.run_id, reason="   ")
    with pytest.raises(
        InvalidRequestError, match="Cancellation reason cannot be empty"
    ):
        use_case.execute(command)


def test_cancel_completed_run_rejected(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that cancelling a completed run raises terminal state error."""
    run = Run(run_id="run-comp", project_id="proj-1")
    run.start_planning()
    run.finish_planning()
    run.submit_prototype("p1")
    run.approve_prototype("client")
    run.start_building()
    run.finish_building("sha1", "workspace/p1")
    run.pass_qa()
    run.complete_deployment("https://app.agency.run")
    fake_repo.save(run)

    use_case = CancelRun(repository=fake_repo, event_bus=fake_bus)
    command = CancelRunCommand(run_id=run.run_id, reason="Cancel completed")

    with pytest.raises(InvalidTerminalStateOperationError, match="terminal state"):
        use_case.execute(command)


def test_cancel_failed_run_rejected(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that cancelling an already failed run raises terminal state error."""
    run = Run(run_id="run-failed", project_id="proj-1")
    run.fail(reason="Syntax failure")
    fake_repo.save(run)

    use_case = CancelRun(repository=fake_repo, event_bus=fake_bus)
    command = CancelRunCommand(run_id=run.run_id, reason="Cancel failed")

    with pytest.raises(InvalidTerminalStateOperationError, match="terminal state"):
        use_case.execute(command)


def test_cancel_repeated_cancellation_rejected(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that cancelling an already cancelled run is rejected."""
    run = Run(run_id="run-repeat", project_id="proj-1")
    run.cancel(reason="Initial cancel")
    fake_repo.save(run)

    use_case = CancelRun(repository=fake_repo, event_bus=fake_bus)
    command = CancelRunCommand(run_id=run.run_id, reason="Second cancel")

    with pytest.raises(InvalidTerminalStateOperationError, match="terminal state"):
        use_case.execute(command)


def test_cancel_run_persistence_failure(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test persistence failure aborts event publishing."""
    run = Run(run_id="run-pfail", project_id="proj-1")
    fake_repo.save(run)

    fake_repo.set_failure(RepositoryError("Storage IO failure"))
    use_case = CancelRun(repository=fake_repo, event_bus=fake_bus)
    command = CancelRunCommand(run_id=run.run_id, reason="Cancel")

    with pytest.raises(RepositoryError, match="Storage IO failure"):
        use_case.execute(command)

    assert len(fake_bus.events) == 0


def test_cancel_run_event_publication_failure(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test event publication failure preserves cancelled state in repo."""
    run = Run(run_id="run-efail", project_id="proj-1")
    fake_repo.save(run)

    fake_bus.set_failure(RuntimeError("Event bus down"))
    use_case = CancelRun(repository=fake_repo, event_bus=fake_bus)
    command = CancelRunCommand(run_id=run.run_id, reason="Cancel")

    with pytest.raises(EventPublicationError, match="event publication failed"):
        use_case.execute(command)

    saved_run = fake_repo.get_by_id(run.run_id)
    assert saved_run is not None
    assert saved_run.state == RunState.CANCELLED
    assert saved_run.cancellation_reason == "Cancel"
