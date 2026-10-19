"""Unit tests for StartRun use case."""

import pytest
from pydantic import ValidationError
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_run_repository import FakeRunRepository

from agency.application.errors import (
    EventPublicationError,
    InvalidRequestError,
    RepositoryError,
)
from agency.application.use_cases.start_run import (
    StartRun,
    StartRunCommand,
)
from agency.domain.entities.brief import Brief
from agency.domain.enums import RunState
from agency.domain.events import RunStarted


@pytest.fixture
def fake_repo() -> FakeRunRepository:
    """Provide a fresh in-memory repository."""
    return FakeRunRepository()


@pytest.fixture
def fake_bus() -> FakeEventBus:
    """Provide a fresh in-memory event bus."""
    return FakeEventBus()


@pytest.fixture
def sample_brief() -> Brief:
    """Provide a valid Brief fixture."""
    return Brief(
        client_name="Acme Corp",
        site_type="Landing Page",
        pages=["home", "pricing"],
        tone="Professional",
        content_notes="B2B audience",
    )


def test_start_run_success(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    sample_brief: Brief,
) -> None:
    """Test standard valid run initialization."""
    use_case = StartRun(repository=fake_repo, event_bus=fake_bus)
    command = StartRunCommand(
        project_id="proj-acme-101",
        brief=sample_brief,
    )

    result = use_case.execute(command)

    assert result.run_id is not None
    assert len(result.run_id) > 0
    assert result.project_id == "proj-acme-101"
    assert result.state == RunState.CREATED

    # Verify repository persistence
    saved_run = fake_repo.get_by_id(result.run_id)
    assert saved_run is not None
    assert saved_run.project_id == "proj-acme-101"
    assert saved_run.state == RunState.CREATED
    assert saved_run.brief == sample_brief

    # Verify event publication
    assert len(fake_bus.events) == 1
    event = fake_bus.events[0]
    assert isinstance(event, RunStarted)
    assert event.run_id == result.run_id
    assert event.project_id == "proj-acme-101"


def test_start_run_explicit_run_id(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    sample_brief: Brief,
) -> None:
    """Test starting a run with a pre-specified run_id."""
    use_case = StartRun(repository=fake_repo, event_bus=fake_bus)
    command = StartRunCommand(
        project_id="proj-custom-id",
        brief=sample_brief,
        run_id="run-custom-001",
    )

    result = use_case.execute(command)
    assert result.run_id == "run-custom-001"
    assert fake_repo.get_by_id("run-custom-001") is not None


def test_start_run_custom_id_generator(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    sample_brief: Brief,
) -> None:
    """Test custom run_id_generator injection."""
    use_case = StartRun(
        repository=fake_repo,
        event_bus=fake_bus,
        run_id_generator=lambda: "run-generated-xyz",
    )
    command = StartRunCommand(
        project_id="proj-gen",
        brief=sample_brief,
    )

    result = use_case.execute(command)
    assert result.run_id == "run-generated-xyz"


def test_start_run_rejects_empty_project_id(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    sample_brief: Brief,
) -> None:
    """Test that empty or whitespace project_id is rejected."""
    use_case = StartRun(repository=fake_repo, event_bus=fake_bus)

    with pytest.raises(ValidationError):
        StartRunCommand(project_id="", brief=sample_brief)

    # Whitespace only
    command = StartRunCommand(project_id="   ", brief=sample_brief)
    with pytest.raises(InvalidRequestError, match="Project ID cannot be empty"):
        use_case.execute(command)


def test_start_run_rejects_empty_run_id(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    sample_brief: Brief,
) -> None:
    """Test that empty or whitespace run_id is rejected."""
    use_case = StartRun(
        repository=fake_repo,
        event_bus=fake_bus,
        run_id_generator=lambda: "   ",
    )
    command = StartRunCommand(
        project_id="proj-valid",
        brief=sample_brief,
    )

    with pytest.raises(InvalidRequestError, match="Run ID cannot be empty"):
        use_case.execute(command)


def test_start_run_persistence_failure_aborts_event_publishing(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    sample_brief: Brief,
) -> None:
    """Test that if repository persistence fails, events are not published."""
    fake_repo.set_failure(RepositoryError("Simulated DB connection failure"))
    use_case = StartRun(repository=fake_repo, event_bus=fake_bus)
    command = StartRunCommand(
        project_id="proj-fail",
        brief=sample_brief,
    )

    with pytest.raises(RepositoryError, match="Simulated DB connection failure"):
        use_case.execute(command)

    # Event bus must receive no events
    assert len(fake_bus.events) == 0


def test_start_run_event_publication_failure_preserves_persisted_state(
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    sample_brief: Brief,
) -> None:
    """Test that event publication failure raises EventPublicationError.

    The truthfully persisted state must remain preserved in the repository.
    """
    fake_bus.set_failure(RuntimeError("Simulated bus outage"))
    use_case = StartRun(
        repository=fake_repo,
        event_bus=fake_bus,
        run_id_generator=lambda: "run-persisted-truth",
    )
    command = StartRunCommand(
        project_id="proj-truth",
        brief=sample_brief,
    )

    with pytest.raises(EventPublicationError, match="event publication failed"):
        use_case.execute(command)

    # Verify that the aggregate was saved and not rolled back
    saved_run = fake_repo.get_by_id("run-persisted-truth")
    assert saved_run is not None
    assert saved_run.run_id == "run-persisted-truth"
    assert saved_run.state == RunState.CREATED
