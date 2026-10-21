"""Unit tests for OfficeStateService and task derivation logic."""

from datetime import UTC, datetime

import pytest
from tests.fakes.fake_artifact_storage import FakeArtifactStorage
from tests.fakes.fake_run_repository import FakeRunRepository

from agency.application.errors import RunNotFoundError
from agency.application.office.models import (
    AgentRoleEnum,
    EmployeeStatusEnum,
    TaskStatusEnum,
    WorkstationEnum,
)
from agency.application.office.service import OfficeStateService
from agency.domain.entities.brief import Brief
from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.domain.events import (
    PlanningCompleted,
    PrototypeReady,
    RunStarted,
)
from agency.infrastructure.persistence.durable_event_feed import DurableEventFeed


@pytest.fixture
def fake_repo() -> FakeRunRepository:
    return FakeRunRepository()


@pytest.fixture
def event_feed() -> DurableEventFeed:
    return DurableEventFeed()


def test_office_state_not_found(fake_repo: FakeRunRepository) -> None:
    service = OfficeStateService(repository=fake_repo)
    with pytest.raises(RunNotFoundError):
        service.get_office_state("missing-run-id")


def test_office_state_created_stage(
    fake_repo: FakeRunRepository,
    event_feed: DurableEventFeed,
) -> None:
    run = Run(run_id="run-created", project_id="proj-1", state=RunState.CREATED)
    fake_repo.save(run)

    service = OfficeStateService(repository=fake_repo, event_feed=event_feed)
    state = service.get_office_state("run-created")

    assert state.run_id == "run-created"
    assert state.project_id == "proj-1"
    assert state.run_status == "CREATED"
    assert state.current_stage == "created"
    assert len(state.employees) == 7
    assert len(state.workstations) == 7
    assert len(state.tasks) == 7

    # In CREATED, planning task is pending
    planning_task = next(t for t in state.tasks if t.task_type == "planning")
    assert planning_task.status == TaskStatusEnum.PENDING

    # Manager task is in_progress
    mgr_task = next(t for t in state.tasks if t.task_type == "orchestration")
    assert mgr_task.status == TaskStatusEnum.IN_PROGRESS


def test_office_state_planning_stage(
    fake_repo: FakeRunRepository,
    event_feed: DurableEventFeed,
) -> None:
    brief = Brief(
        client_name="TestCo",
        site_type="landing",
        pages=["Home"],
        tone="professional",
        content_notes="Test content",
    )
    run = Run(
        run_id="run-planning", project_id="proj-1", brief=brief, state=RunState.PLANNING
    )
    fake_repo.save(run)

    # Record RunStarted event
    now = datetime.now(UTC)
    event_feed.record_event(
        RunStarted(run_id="run-planning", project_id="proj-1", occurred_at=now)
    )

    service = OfficeStateService(repository=fake_repo, event_feed=event_feed)
    state = service.get_office_state("run-planning")

    # PM employee working at planning desk
    pm_emp = next(e for e in state.employees if e.role == AgentRoleEnum.PM)
    assert pm_emp.status == EmployeeStatusEnum.WORKING
    assert pm_emp.workstation == WorkstationEnum.PLANNING_DESK

    # Planning desk is active
    planning_station = next(
        w for w in state.workstations if w.id == WorkstationEnum.PLANNING_DESK
    )
    assert planning_station.status == "active"
    assert planning_station.active_task_id == f"{run.run_id}-task-planning"


def test_office_state_awaiting_approval(
    fake_repo: FakeRunRepository,
    event_feed: DurableEventFeed,
) -> None:
    run = Run(
        run_id="run-approval",
        project_id="proj-1",
        state=RunState.AWAITING_APPROVAL,
        prototype_ref="https://preview.agency.run/p1/rev0",
    )
    fake_repo.save(run)

    t0 = datetime.now(UTC)
    event_feed.record_event(
        RunStarted(run_id="run-approval", project_id="proj-1", occurred_at=t0)
    )
    event_feed.record_event(PlanningCompleted(run_id="run-approval", occurred_at=t0))
    event_feed.record_event(
        PrototypeReady(run_id="run-approval", prototype_ref="preview-1", occurred_at=t0)
    )

    service = OfficeStateService(repository=fake_repo, event_feed=event_feed)
    state = service.get_office_state("run-approval")

    # Reviewer employee is WAITING_APPROVAL
    reviewer = next(e for e in state.employees if e.role == AgentRoleEnum.REVIEWER)
    assert reviewer.status == EmployeeStatusEnum.WAITING_APPROVAL
    assert reviewer.workstation == WorkstationEnum.REVIEW_AREA
    assert reviewer.is_logical_role is True

    review_task = next(t for t in state.tasks if t.task_type == "approval")
    assert review_task.status == TaskStatusEnum.WAITING_APPROVAL
    assert state.active_task_id == review_task.id


def test_office_state_building_and_testing_with_artifacts(
    fake_repo: FakeRunRepository,
    event_feed: DurableEventFeed,
) -> None:
    run = Run(run_id="run-building", project_id="proj-1", state=RunState.BUILDING)
    fake_repo.save(run)

    storage = FakeArtifactStorage()
    for item in ("spec-1.json", "design-tokens.css", "workspace.zip"):
        storage.save_artifact(
            run_id="run-building",
            artifact_id=item,
            artifact_type="text/plain",
            display_name=item,
            mime_type="text/plain",
            content=b"test",
        )
    service = OfficeStateService(
        repository=fake_repo, event_feed=event_feed, artifact_storage=storage
    )
    state = service.get_office_state("run-building")

    builder = next(e for e in state.employees if e.role == AgentRoleEnum.BUILDER)
    assert builder.status == EmployeeStatusEnum.WORKING

    build_task = next(t for t in state.tasks if t.task_type == "build")
    assert build_task.status == TaskStatusEnum.IN_PROGRESS
    assert "workspace.zip" in build_task.related_artifact_ids


def test_office_state_completed(
    fake_repo: FakeRunRepository,
    event_feed: DurableEventFeed,
) -> None:
    run = Run(run_id="run-comp", project_id="proj-1", state=RunState.COMPLETED)
    fake_repo.save(run)

    service = OfficeStateService(repository=fake_repo, event_feed=event_feed)
    state = service.get_office_state("run-comp")

    assert state.run_status == "COMPLETED"
    for task in state.tasks:
        assert task.status == TaskStatusEnum.COMPLETED

    manager = next(e for e in state.employees if e.role == AgentRoleEnum.MANAGER)
    assert manager.status == EmployeeStatusEnum.COMPLETED


def test_office_state_failed(
    fake_repo: FakeRunRepository,
    event_feed: DurableEventFeed,
) -> None:
    run = Run(
        run_id="run-fail",
        project_id="proj-1",
        state=RunState.FAILED,
        failure_reason="Sandbox execution timeout in build step.",
    )
    fake_repo.save(run)

    service = OfficeStateService(repository=fake_repo, event_feed=event_feed)
    state = service.get_office_state("run-fail")

    assert "Sandbox execution timeout in build step." in state.blockers
    manager = next(e for e in state.employees if e.role == AgentRoleEnum.MANAGER)
    assert manager.status == EmployeeStatusEnum.FAILED

    tasks = service.get_run_tasks("run-fail")
    assert len(tasks) == 7
