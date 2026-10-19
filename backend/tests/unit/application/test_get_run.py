"""Unit tests for GetRun use case."""

import pytest
from tests.fakes.fake_run_repository import FakeRunRepository

from agency.application.errors import InvalidRequestError, RunNotFoundError
from agency.application.use_cases.get_run import GetRun
from agency.domain.entities.run import Run
from agency.domain.enums import RunState


@pytest.fixture
def fake_repo() -> FakeRunRepository:
    """Provide a fresh in-memory repository."""
    return FakeRunRepository()


def test_get_run_success(fake_repo: FakeRunRepository) -> None:
    """Test retrieving an existing run by ID."""
    run = Run(run_id="run-test-get", project_id="proj-get")
    fake_repo.save(run)

    use_case = GetRun(repository=fake_repo)
    result = use_case.execute(run_id="run-test-get")

    assert result.run_id == "run-test-get"
    assert result.project_id == "proj-get"
    assert result.state == RunState.CREATED


def test_get_run_not_found(fake_repo: FakeRunRepository) -> None:
    """Test retrieving a non-existent run raises RunNotFoundError."""
    use_case = GetRun(repository=fake_repo)

    with pytest.raises(RunNotFoundError, match="Run 'missing-id' was not found"):
        use_case.execute(run_id="missing-id")


def test_get_run_empty_id_rejected(fake_repo: FakeRunRepository) -> None:
    """Test that empty or whitespace run_id is rejected."""
    use_case = GetRun(repository=fake_repo)

    with pytest.raises(InvalidRequestError, match="Run ID cannot be empty"):
        use_case.execute(run_id="   ")


def test_get_run_returned_object_mutation_isolation(
    fake_repo: FakeRunRepository,
) -> None:
    """Test that modifying returned aggregate does not alter stored repository state."""
    run = Run(run_id="run-isolation", project_id="proj-iso")
    fake_repo.save(run)

    use_case = GetRun(repository=fake_repo)
    retrieved = use_case.execute(run_id="run-isolation")

    # Mutate retrieved object in caller space
    retrieved.project_id = "mutated-project"

    # Query repository again
    fresh = use_case.execute(run_id="run-isolation")
    assert fresh.project_id == "proj-iso"
