"""Unit tests for ApprovePrototype use case."""

import pytest
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_run_repository import FakeRunRepository

from agency.application.errors import (
    EventPublicationError,
    RepositoryError,
    RunNotFoundError,
)
from agency.application.use_cases.approve_prototype import (
    ApprovePrototype,
    ApprovePrototypeCommand,
)
from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.domain.errors import (
    ApprovalRequiredError,
    InvalidApprovalError,
)
from agency.domain.events import PrototypeApproved


@pytest.fixture
def fake_repo() -> FakeRunRepository:
    """Provide a fresh in-memory repository."""
    return FakeRunRepository()


@pytest.fixture
def fake_bus() -> FakeEventBus:
    """Provide a fresh in-memory event bus."""
    return FakeEventBus()


def create_awaiting_approval_run(
    run_id: str = "run-approval-1",
    prototype_ref: str = "proto-v1-ref",
) -> Run:
    """Helper to instantiate and advance a Run to AWAITING_APPROVAL."""
    run = Run(run_id=run_id, project_id="proj-app-1")
    run.start_planning()
    run.finish_planning()
    run.submit_prototype(prototype_ref=prototype_ref)
    run.clear_events()
    return run


def test_approve_prototype_success(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test successful prototype approval."""
    run = create_awaiting_approval_run()
    fake_repo.save(run)

    use_case = ApprovePrototype(repository=fake_repo, event_bus=fake_bus)
    command = ApprovePrototypeCommand(
        run_id=run.run_id,
        approver="client-lead@example.com",
    )

    result = use_case.execute(command)

    assert result.run_id == run.run_id
    assert result.state == RunState.AWAITING_APPROVAL
    assert result.approver == "client-lead@example.com"
    assert result.approved_at is not None

    # Check repository persistence
    saved_run = fake_repo.get_by_id(run.run_id)
    assert saved_run is not None
    assert saved_run.approval_recorded is True
    assert saved_run.approver == "client-lead@example.com"

    # Check event publication
    assert len(fake_bus.events) == 1
    event = fake_bus.events[0]
    assert isinstance(event, PrototypeApproved)
    assert event.run_id == run.run_id
    assert event.prototype_ref == "proto-v1-ref"
    assert event.approver == "client-lead@example.com"


def test_approve_prototype_with_new_prototype_ref(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test approval that explicitly supplies a new prototype_ref."""
    run = create_awaiting_approval_run()
    fake_repo.save(run)

    use_case = ApprovePrototype(repository=fake_repo, event_bus=fake_bus)
    command = ApprovePrototypeCommand(
        run_id=run.run_id,
        approver="stakeholder@example.com",
        prototype_ref="proto-v2-updated",
    )

    result = use_case.execute(command)
    assert result.run_id == run.run_id

    saved_run = fake_repo.get_by_id(run.run_id)
    assert saved_run is not None
    assert saved_run.prototype_ref == "proto-v2-updated"


def test_approve_prototype_missing_run_raises_not_found(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that non-existent run raises RunNotFoundError."""
    use_case = ApprovePrototype(repository=fake_repo, event_bus=fake_bus)
    command = ApprovePrototypeCommand(
        run_id="non-existent-run",
        approver="client",
    )

    with pytest.raises(RunNotFoundError, match="Run 'non-existent-run' was not found"):
        use_case.execute(command)


def test_approve_prototype_wrong_state_rejected(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that approving a run in CREATED or PLANNING state fails."""
    run = Run(run_id="run-created", project_id="proj-1")
    fake_repo.save(run)

    use_case = ApprovePrototype(repository=fake_repo, event_bus=fake_bus)
    command = ApprovePrototypeCommand(run_id=run.run_id, approver="client")

    with pytest.raises(InvalidApprovalError, match="Must be in 'AWAITING_APPROVAL'"):
        use_case.execute(command)


def test_approve_prototype_duplicate_approval_rejected(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that approving an already-approved prototype fails."""
    run = create_awaiting_approval_run()
    use_case = ApprovePrototype(repository=fake_repo, event_bus=fake_bus)
    command = ApprovePrototypeCommand(run_id=run.run_id, approver="client")

    fake_repo.save(run)
    use_case.execute(command)

    # Second approval attempt must be rejected
    with pytest.raises(InvalidApprovalError, match="already been approved"):
        use_case.execute(command)


def test_approve_prototype_missing_prototype_ref_rejected(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that approval fails if no prototype reference exists."""
    run = Run(
        run_id="run-no-ref",
        project_id="proj-1",
        state=RunState.AWAITING_APPROVAL,
    )
    fake_repo.save(run)

    use_case = ApprovePrototype(repository=fake_repo, event_bus=fake_bus)
    command = ApprovePrototypeCommand(run_id=run.run_id, approver="client")

    with pytest.raises(InvalidApprovalError, match="Missing prototype reference"):
        use_case.execute(command)


def test_approve_prototype_persistence_failure(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that repository save failure aborts event publishing."""
    run = create_awaiting_approval_run()
    fake_repo.save(run)

    fake_repo.set_failure(RepositoryError("Persistence layer unavailable"))
    use_case = ApprovePrototype(repository=fake_repo, event_bus=fake_bus)
    command = ApprovePrototypeCommand(run_id=run.run_id, approver="client")

    with pytest.raises(RepositoryError, match="Persistence layer unavailable"):
        use_case.execute(command)

    assert len(fake_bus.events) == 0


def test_approve_prototype_event_publication_failure(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
) -> None:
    """Test that event publication failure preserves the approved state in repo."""
    run = create_awaiting_approval_run()
    fake_repo.save(run)

    fake_bus.set_failure(RuntimeError("Bus queue broken"))
    use_case = ApprovePrototype(repository=fake_repo, event_bus=fake_bus)
    command = ApprovePrototypeCommand(
        run_id=run.run_id,
        approver="client-persistent",
    )

    with pytest.raises(EventPublicationError, match="event publication failed"):
        use_case.execute(command)

    saved_run = fake_repo.get_by_id(run.run_id)
    assert saved_run is not None
    assert saved_run.approval_recorded is True
    assert saved_run.approver == "client-persistent"


def test_approval_cannot_be_bypassed_to_building(
    fake_repo: FakeRunRepository,
) -> None:
    """Test domain invariant that BUILDING cannot be reached without approval."""
    run = create_awaiting_approval_run()
    fake_repo.save(run)

    assert run.approval_recorded is False
    with pytest.raises(ApprovalRequiredError):
        run.start_building()
