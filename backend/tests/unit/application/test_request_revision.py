"""Unit tests for RequestRevision use case."""

import pytest
from pydantic import ValidationError
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_run_repository import FakeRunRepository

from agency.application.errors import (
    EventPublicationError,
    InvalidRequestError,
    RepositoryError,
    RevisionLimitExceededError,
    RunNotFoundError,
)
from agency.application.use_cases.request_revision import (
    RequestRevision,
    RequestRevisionCommand,
)
from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.domain.errors import InvalidRevisionRequestError
from agency.domain.events import RevisionRequested


@pytest.fixture
def fake_repo() -> FakeRunRepository:
    """Provide a fresh in-memory repository."""
    return FakeRunRepository()


@pytest.fixture
def fake_bus() -> FakeEventBus:
    """Provide a fresh in-memory event bus."""
    return FakeEventBus()


def create_awaiting_approval_run(run_id: str = "run-rev-1") -> Run:
    """Helper to instantiate and advance a Run to AWAITING_APPROVAL."""
    run = Run(run_id=run_id, project_id="proj-rev-1")
    run.start_planning()
    run.finish_planning()
    run.submit_prototype(prototype_ref="proto-v1")
    run.clear_events()
    return run


def test_request_revision_success(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test successful revision request."""
    run = create_awaiting_approval_run()
    fake_repo.save(run)

    use_case = RequestRevision(repository=fake_repo, event_bus=fake_bus)
    command = RequestRevisionCommand(
        run_id=run.run_id,
        reason="Please update color scheme to dark mode.",
    )

    result = use_case.execute(command)

    assert result.run_id == run.run_id
    assert result.state == RunState.PROTOTYPING
    assert result.revision_count == 1
    assert result.revision_history == ["Please update color scheme to dark mode."]

    # Check persistence
    saved_run = fake_repo.get_by_id(run.run_id)
    assert saved_run is not None
    assert saved_run.state == RunState.PROTOTYPING
    assert saved_run.revision_count == 1
    assert saved_run.revision_history == ["Please update color scheme to dark mode."]

    # Check event publication
    assert len(fake_bus.events) == 1
    event = fake_bus.events[0]
    assert isinstance(event, RevisionRequested)
    assert event.run_id == run.run_id
    assert event.revision_number == 1
    assert event.reason == "Please update color scheme to dark mode."


def test_request_revision_rejects_empty_comment(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that empty or whitespace revision reason is rejected."""
    run = create_awaiting_approval_run()
    fake_repo.save(run)

    use_case = RequestRevision(repository=fake_repo, event_bus=fake_bus)

    with pytest.raises(ValidationError):
        RequestRevisionCommand(run_id=run.run_id, reason="")

    command = RequestRevisionCommand(run_id=run.run_id, reason="   ")
    with pytest.raises(InvalidRequestError, match="Revision reason cannot be empty"):
        use_case.execute(command)


def test_request_revision_wrong_state_rejected(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that requesting revision when not AWAITING_APPROVAL is rejected."""
    run = Run(run_id="run-created", project_id="proj-1")
    fake_repo.save(run)

    use_case = RequestRevision(repository=fake_repo, event_bus=fake_bus)
    command = RequestRevisionCommand(
        run_id=run.run_id,
        reason="Need changes",
    )

    with pytest.raises(
        InvalidRevisionRequestError, match="Must be in 'AWAITING_APPROVAL'"
    ):
        use_case.execute(command)


def test_request_revision_missing_run_raises_not_found(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that requesting revision for non-existent run raises RunNotFoundError."""
    use_case = RequestRevision(repository=fake_repo, event_bus=fake_bus)
    command = RequestRevisionCommand(
        run_id="non-existent",
        reason="Revise",
    )

    with pytest.raises(RunNotFoundError, match="Run 'non-existent' was not found"):
        use_case.execute(command)


def test_three_permitted_revisions_and_fourth_fails(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test enforcing exactly three revisions, with fourth rejected."""
    run = create_awaiting_approval_run()
    fake_repo.save(run)

    use_case = RequestRevision(repository=fake_repo, event_bus=fake_bus)

    # Revision 1
    cmd1 = RequestRevisionCommand(run_id=run.run_id, reason="Feedback 1")
    res1 = use_case.execute(cmd1)
    assert res1.revision_count == 1
    assert res1.state == RunState.PROTOTYPING

    # Re-submit prototype to enter AWAITING_APPROVAL again
    r1 = fake_repo.get_by_id(run.run_id)
    assert r1 is not None
    r1.submit_prototype("proto-v2")
    fake_repo.save(r1)

    # Revision 2
    cmd2 = RequestRevisionCommand(run_id=run.run_id, reason="Feedback 2")
    res2 = use_case.execute(cmd2)
    assert res2.revision_count == 2
    assert res2.state == RunState.PROTOTYPING

    # Re-submit prototype
    r2 = fake_repo.get_by_id(run.run_id)
    assert r2 is not None
    r2.submit_prototype("proto-v3")
    fake_repo.save(r2)

    # Revision 3
    cmd3 = RequestRevisionCommand(run_id=run.run_id, reason="Feedback 3")
    res3 = use_case.execute(cmd3)
    assert res3.revision_count == 3
    assert res3.state == RunState.PROTOTYPING

    # Re-submit prototype
    r3 = fake_repo.get_by_id(run.run_id)
    assert r3 is not None
    r3.submit_prototype("proto-v4")
    fake_repo.save(r3)

    # Revision 4 must fail with RevisionLimitExceededError
    cmd4 = RequestRevisionCommand(run_id=run.run_id, reason="Feedback 4")
    with pytest.raises(RevisionLimitExceededError) as exc_info:
        use_case.execute(cmd4)

    assert exc_info.value.run_id == run.run_id
    assert exc_info.value.max_revisions == 3

    # Check history remains intact and capped at 3
    persisted = fake_repo.get_by_id(run.run_id)
    assert persisted is not None
    assert persisted.revision_count == 3
    assert persisted.revision_history == ["Feedback 1", "Feedback 2", "Feedback 3"]


def test_request_revision_persistence_failure(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that persistence error aborts event publication."""
    run = create_awaiting_approval_run()
    fake_repo.save(run)

    fake_repo.set_failure(RepositoryError("DB write failed"))
    use_case = RequestRevision(repository=fake_repo, event_bus=fake_bus)
    command = RequestRevisionCommand(run_id=run.run_id, reason="Need changes")

    with pytest.raises(RepositoryError, match="DB write failed"):
        use_case.execute(command)

    assert len(fake_bus.events) == 0


def test_request_revision_event_publication_failure(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test event publication failure preserves the persisted revision state."""
    run = create_awaiting_approval_run()
    fake_repo.save(run)

    fake_bus.set_failure(RuntimeError("Bus connection dropped"))
    use_case = RequestRevision(repository=fake_repo, event_bus=fake_bus)
    command = RequestRevisionCommand(
        run_id=run.run_id,
        reason="Preserve this revision",
    )

    with pytest.raises(EventPublicationError, match="event publication failed"):
        use_case.execute(command)

    saved_run = fake_repo.get_by_id(run.run_id)
    assert saved_run is not None
    assert saved_run.revision_count == 1
    assert saved_run.revision_history == ["Preserve this revision"]
    assert saved_run.state == RunState.PROTOTYPING
