"""Unit tests for ListRuns use case."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from tests.fakes.fake_run_repository import FakeRunRepository

from agency.application.use_cases.list_runs import (
    ListRuns,
    ListRunsQuery,
)
from agency.domain.entities.run import Run
from agency.domain.enums import RunState


@pytest.fixture
def fake_repo() -> FakeRunRepository:
    """Provide a fresh in-memory repository."""
    return FakeRunRepository()


def test_list_runs_empty(fake_repo: FakeRunRepository) -> None:
    """Test listing runs when repository is empty."""
    use_case = ListRuns(repository=fake_repo)
    result = use_case.execute()

    assert result.items == []
    assert result.total == 0
    assert result.limit == 50
    assert result.offset == 0


def test_list_runs_deterministic_ordering(fake_repo: FakeRunRepository) -> None:
    """Test runs are ordered deterministically by created_at, then run_id."""
    base_time = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    r1 = Run(
        run_id="run-b",
        project_id="p1",
        created_at=base_time + timedelta(minutes=5),
    )
    r2 = Run(
        run_id="run-a",
        project_id="p1",
        created_at=base_time,
    )
    r3 = Run(
        run_id="run-c",
        project_id="p1",
        created_at=base_time + timedelta(minutes=10),
    )
    fake_repo.save(r1)
    fake_repo.save(r2)
    fake_repo.save(r3)

    use_case = ListRuns(repository=fake_repo)
    result = use_case.execute()

    assert result.total == 3
    assert len(result.items) == 3
    assert [r.run_id for r in result.items] == ["run-a", "run-b", "run-c"]


def test_list_runs_pagination(fake_repo: FakeRunRepository) -> None:
    """Test limit and offset pagination behavior."""
    base_time = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    for i in range(5):
        run = Run(
            run_id=f"run-{i:02d}",
            project_id=f"proj-{i}",
            created_at=base_time + timedelta(minutes=i),
        )
        fake_repo.save(run)

    use_case = ListRuns(repository=fake_repo)

    # Page 1: limit 2, offset 0
    page1 = use_case.execute(ListRunsQuery(limit=2, offset=0))
    assert page1.total == 5
    assert len(page1.items) == 2
    assert [r.run_id for r in page1.items] == ["run-00", "run-01"]

    # Page 2: limit 2, offset 2
    page2 = use_case.execute(ListRunsQuery(limit=2, offset=2))
    assert page2.total == 5
    assert len(page2.items) == 2
    assert [r.run_id for r in page2.items] == ["run-02", "run-03"]

    # Page 3: limit 2, offset 4
    page3 = use_case.execute(ListRunsQuery(limit=2, offset=4))
    assert page3.total == 5
    assert len(page3.items) == 1
    assert [r.run_id for r in page3.items] == ["run-04"]

    # Page 4: offset beyond total
    page4 = use_case.execute(ListRunsQuery(limit=2, offset=10))
    assert page4.total == 5
    assert len(page4.items) == 0


def test_list_runs_filtering_by_state(fake_repo: FakeRunRepository) -> None:
    """Test filtering runs by RunState."""
    r1 = Run(run_id="run-created", project_id="p1", state=RunState.CREATED)
    r2 = Run(run_id="run-cancelled", project_id="p1", state=RunState.CANCELLED)
    fake_repo.save(r1)
    fake_repo.save(r2)

    use_case = ListRuns(repository=fake_repo)

    created_result = use_case.execute(ListRunsQuery(state=RunState.CREATED))
    assert created_result.total == 1
    assert len(created_result.items) == 1
    assert created_result.items[0].run_id == "run-created"

    cancelled_result = use_case.execute(ListRunsQuery(state=RunState.CANCELLED))
    assert cancelled_result.total == 1
    assert len(cancelled_result.items) == 1
    assert cancelled_result.items[0].run_id == "run-cancelled"

    completed_result = use_case.execute(ListRunsQuery(state=RunState.COMPLETED))
    assert completed_result.total == 0
    assert len(completed_result.items) == 0


def test_list_runs_invalid_pagination_parameters() -> None:
    """Test that invalid limit and offset values are rejected by schema."""
    with pytest.raises(ValidationError):
        ListRunsQuery(limit=0)

    with pytest.raises(ValidationError):
        ListRunsQuery(limit=101)

    with pytest.raises(ValidationError):
        ListRunsQuery(offset=-1)
