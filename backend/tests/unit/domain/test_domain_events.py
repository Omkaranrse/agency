"""Unit tests for domain events and aggregate event buffering."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.domain.errors import InvalidStateTransitionError
from agency.domain.events import (
    BuildCompleted,
    BuildStarted,
    DeploymentCompleted,
    PlanningCompleted,
    PrototypeApproved,
    PrototypeReady,
    QAFailed,
    QAPassed,
    RevisionRequested,
    RunCancelled,
    RunFailed,
    RunStarted,
)


def mutate_attr(obj: object, name: str, value: object) -> None:
    """Helper to attempt dynamic mutation on frozen objects."""
    setattr(obj, name, value)


def test_domain_event_immutability_and_structure() -> None:
    """Test that domain events are immutable and require UTC-aware timestamps."""
    event = RunStarted(
        run_id="run-1",
        project_id="proj-1",
        occurred_at=datetime.now(UTC),
    )
    assert event.run_id == "run-1"
    assert event.project_id == "proj-1"
    assert event.event_id is not None

    with pytest.raises(ValidationError):
        mutate_attr(event, "project_id", "proj-2")


def test_domain_event_rejects_naive_timestamp() -> None:
    """Test that timezone-naive datetime raises ValidationError on DomainEvent."""
    with pytest.raises(ValidationError):
        RunStarted(
            run_id="run-1",
            project_id="proj-1",
            occurred_at=datetime.now(),  # naive
        )


def test_aggregate_event_collection_and_clearing() -> None:
    """Test collect_events and clear_events APIs on Run aggregate."""
    run = Run(project_id="proj-1")
    assert len(run.collect_events()) == 0

    run.start_planning()
    events = run.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], RunStarted)

    # collect_events does not drain
    assert len(run.collect_events()) == 1

    # clear_events drains buffer
    drained = run.clear_events()
    assert len(drained) == 1
    assert len(run.collect_events()) == 0


def test_failed_operations_do_not_emit_events() -> None:
    """Invariant: Failed operations must not emit misleading success events."""
    run = Run(project_id="proj-1")
    initial_event_count = len(run.collect_events())

    with pytest.raises(InvalidStateTransitionError):
        run.transition_to(RunState.BUILDING)  # Illegal jump

    assert len(run.collect_events()) == initial_event_count


def test_all_lifecycle_events_emitted_in_workflow() -> None:
    """Verify lifecycle event types emitted at each domain step."""
    run = Run(project_id="proj-1")

    # 1. RunStarted
    run.start_planning()
    events = run.clear_events()
    assert any(isinstance(e, RunStarted) for e in events)

    # 2. PlanningCompleted
    run.finish_planning()
    events = run.clear_events()
    assert any(isinstance(e, PlanningCompleted) for e in events)

    # 3. PrototypeReady
    run.submit_prototype("proto-alpha")
    events = run.clear_events()
    assert any(isinstance(e, PrototypeReady) for e in events)

    # 4. RevisionRequested
    run.request_revision(reason="Needs dark theme")
    events = run.clear_events()
    assert any(isinstance(e, RevisionRequested) for e in events)

    # Resubmit & 5. PrototypeApproved
    run.submit_prototype("proto-beta")
    run.approve_prototype(approver="client@brand.com")
    events = run.clear_events()
    assert any(isinstance(e, PrototypeApproved) for e in events)

    # 6. BuildStarted
    run.start_building(commit_sha="abc1234")
    events = run.clear_events()
    assert any(isinstance(e, BuildStarted) for e in events)

    # 7. BuildCompleted
    run.finish_building(commit_sha="abc1234", workspace_path="/ws/1")
    events = run.clear_events()
    assert any(isinstance(e, BuildCompleted) for e in events)

    # 8. QAPassed
    run.pass_qa(total_checks=10)
    events = run.clear_events()
    assert any(isinstance(e, QAPassed) for e in events)

    # 9. DeploymentCompleted
    run.complete_deployment(url="https://agency.run", is_production=True)
    events = run.clear_events()
    assert any(isinstance(e, DeploymentCompleted) for e in events)


def test_failure_and_cancellation_events() -> None:
    """Verify RunFailed and RunCancelled events recorded on failure/cancel."""
    run1 = Run(project_id="proj-fail")
    run1.start_planning()
    run1.clear_events()
    run1.fail(reason="LLM quota exceeded")
    events1 = run1.clear_events()
    assert len(events1) == 1
    assert isinstance(events1[0], RunFailed)
    assert events1[0].reason == "LLM quota exceeded"
    assert events1[0].from_state == RunState.PLANNING

    run2 = Run(project_id="proj-cancel")
    run2.cancel(reason="Client changed mind")
    events2 = run2.clear_events()
    assert len(events2) == 1
    assert isinstance(events2[0], RunCancelled)
    assert events2[0].reason == "Client changed mind"
    assert events2[0].from_state == RunState.CREATED


def test_qa_failed_event() -> None:
    """Verify QAFailed event is emitted when QA checks fail."""
    run = Run(project_id="proj-qa", state=RunState.TESTING)
    run.fail_qa(
        reason="Security vulnerability CVE-2024-XXXX",
        failed_checks=["npm audit", "owasp zap"],
    )
    events = run.clear_events()
    qa_failed_events = [e for e in events if isinstance(e, QAFailed)]
    assert len(qa_failed_events) == 1
    assert qa_failed_events[0].failed_checks == ["npm audit", "owasp zap"]
    run_failed_events = [e for e in events if isinstance(e, RunFailed)]
    assert len(run_failed_events) == 1
