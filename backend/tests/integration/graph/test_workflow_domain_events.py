"""Integration tests: Domain event emission, ordering, and payload hygiene."""

from tests.fakes.fake_qa_service import make_failing_qa_report
from tests.integration.graph.conftest import build_test_harness, make_test_brief

from agency.application.graph.approval import ApprovalDecision, ApprovalDecisionType
from agency.domain.events import (
    BuildCompleted,
    BuildStarted,
    DeploymentCompleted,
    DeploymentStarted,
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
from agency.infrastructure.persistence import create_in_memory_checkpointer


def test_domain_events_emitted_in_exact_order_for_happy_path() -> None:
    """Happy path workflow emits domain events in order without secrets."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()

    # 1. Start workflow to preview interrupt
    harness.service.start_workflow(
        brief=brief,
        run_id="run-events-happy",
        project_id="elena-events",
    )

    events_phase_1 = harness.event_bus.events
    assert len(events_phase_1) == 3
    assert isinstance(events_phase_1[0], RunStarted)
    assert isinstance(events_phase_1[1], PlanningCompleted)
    assert isinstance(events_phase_1[2], PrototypeReady)

    # 2. Submit human approval
    decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=0,
        approver="client-elena",
    )
    harness.service.submit_approval("run-events-happy", decision)

    all_events = harness.event_bus.events
    assert len(all_events) == 11

    # Verify complete chronological progression
    assert isinstance(all_events[3], PrototypeApproved)
    assert all_events[3].approver == "client-elena"
    assert isinstance(all_events[4], BuildStarted)
    assert isinstance(all_events[5], BuildStarted)
    assert isinstance(all_events[6], BuildCompleted)
    assert isinstance(all_events[7], BuildCompleted)
    assert isinstance(all_events[8], QAPassed)
    assert isinstance(all_events[9], DeploymentStarted)
    assert isinstance(all_events[10], DeploymentCompleted)
    assert all_events[10].is_production is True

    # Check payload hygiene across all emitted events:
    # No credentials, API keys, or raw prompts in domain event payloads
    sensitive_markers = ["sk-", "api_key", "secret", "bearer", "password"]
    for event in all_events:
        assert event.run_id == "run-events-happy"
        event_str = event.model_dump_json().lower()
        for marker in sensitive_markers:
            assert marker not in event_str


def test_domain_events_for_revision_loop() -> None:
    """Revision requests emit RevisionRequested and subsequent PrototypeReady."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()
    harness.service.start_workflow(
        brief=brief,
        run_id="run-events-rev",
        project_id="elena-events-rev",
    )

    harness.event_bus.clear()

    # Submit revision
    revise_decision = ApprovalDecision(
        decision=ApprovalDecisionType.REVISE,
        revision=0,
        comment="Adjust timber palette warmth",
    )
    harness.service.submit_approval("run-events-rev", revise_decision)

    events = harness.event_bus.events
    assert len(events) == 2
    assert isinstance(events[0], RevisionRequested)
    assert events[0].revision_number == 1
    assert "Adjust timber palette" in events[0].reason
    assert isinstance(events[1], PrototypeReady)
    assert "rev1" in events[1].prototype_ref


def test_domain_events_for_qa_exhaustion_and_cancellation() -> None:
    """Exhausted repair cycles emit QAFailed and RunFailed."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    # Configure permanent QA failure
    harness.qa_service.set_report(make_failing_qa_report(failing_checks=["a11y"]))

    brief = make_test_brief()
    harness.service.start_workflow(
        brief=brief,
        run_id="run-events-qa-fail",
        project_id="elena-qa-fail",
    )

    harness.event_bus.clear()

    decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=0,
        approver="client-elena",
    )
    harness.service.submit_approval("run-events-qa-fail", decision)

    events = harness.event_bus.events
    # Expected: PrototypeApproved, BuildStarted, BuildCompleted, QAFailed, RunFailed
    event_types = [type(e) for e in events]
    assert PrototypeApproved in event_types
    assert BuildStarted in event_types
    assert BuildCompleted in event_types
    assert QAFailed in event_types
    assert RunFailed in event_types


def test_cancellation_emits_run_cancelled_event() -> None:
    """Explicit workflow cancellation emits RunCancelled event with reason."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()
    harness.service.start_workflow(
        brief=brief,
        run_id="run-events-cancel",
        project_id="elena-cancel-evt",
    )

    harness.event_bus.clear()

    harness.service.request_cancellation(
        run_id="run-events-cancel",
        reason="Client opted out",
    )

    events = harness.event_bus.events
    assert len(events) == 1
    assert isinstance(events[0], RunCancelled)
    assert events[0].reason == "Client opted out"
