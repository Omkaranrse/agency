"""Unit tests for Run aggregate state machine and transition invariants."""

from datetime import UTC, datetime

import pytest

from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.domain.errors import (
    ApprovalRequiredError,
    DomainInvariantError,
    InvalidApprovalError,
    InvalidRevisionRequestError,
    InvalidStateTransitionError,
    InvalidTerminalStateOperationError,
)


def assert_state(run: Run, expected: RunState) -> None:
    """Helper to verify aggregate state without literal narrowing in caller."""
    assert run.state == expected


@pytest.fixture
def base_run() -> Run:
    """Fixture providing a fresh Run aggregate in CREATED state."""
    return Run(project_id="proj-agency-001")


def test_happy_path_workflow(base_run: Run) -> None:
    """Test full sequential workflow from CREATED through to COMPLETED."""
    t0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 1, 1, 10, 5, tzinfo=UTC)
    t2 = datetime(2026, 1, 1, 10, 10, tzinfo=UTC)
    t3 = datetime(2026, 1, 1, 10, 15, tzinfo=UTC)
    t4 = datetime(2026, 1, 1, 10, 20, tzinfo=UTC)
    t5 = datetime(2026, 1, 1, 10, 25, tzinfo=UTC)
    t6 = datetime(2026, 1, 1, 10, 30, tzinfo=UTC)
    t7 = datetime(2026, 1, 1, 10, 35, tzinfo=UTC)

    # CREATED -> PLANNING
    base_run.start_planning(at=t0)
    assert_state(base_run, RunState.PLANNING)
    assert base_run.updated_at == t0

    # PLANNING -> PROTOTYPING
    base_run.finish_planning(at=t1)
    assert_state(base_run, RunState.PROTOTYPING)
    assert base_run.updated_at == t1

    # PROTOTYPING -> AWAITING_APPROVAL
    base_run.submit_prototype(prototype_ref="proto-v1-astro", at=t2)
    assert_state(base_run, RunState.AWAITING_APPROVAL)
    assert base_run.prototype_ref == "proto-v1-astro"
    assert base_run.updated_at == t2

    # Human Approval Gate
    base_run.approve_prototype(approver="client-lead@example.com", at=t3)
    assert base_run.approval_recorded is True
    assert base_run.approver == "client-lead@example.com"
    # Workflow state remains awaiting until execution starts
    assert_state(base_run, RunState.AWAITING_APPROVAL)

    # AWAITING_APPROVAL -> BUILDING
    base_run.start_building(commit_sha="c0ffee1", at=t4)
    assert_state(base_run, RunState.BUILDING)
    assert base_run.updated_at == t4

    # BUILDING -> TESTING
    base_run.finish_building(commit_sha="c0ffee1", workspace_path="/ws/1", at=t5)
    assert_state(base_run, RunState.TESTING)
    assert base_run.updated_at == t5

    # TESTING -> DEPLOYING
    base_run.pass_qa(total_checks=5, at=t6)
    assert_state(base_run, RunState.DEPLOYING)
    assert base_run.updated_at == t6

    # DEPLOYING -> COMPLETED
    base_run.complete_deployment(url="https://agency.run", at=t7)
    assert_state(base_run, RunState.COMPLETED)
    assert base_run.updated_at == t7


def test_approval_gate_prevents_building_without_approval(base_run: Run) -> None:
    """Invariant: Run cannot transition to BUILDING without prototype approval."""
    base_run.start_planning()
    base_run.finish_planning()
    base_run.submit_prototype("proto-ref")
    assert_state(base_run, RunState.AWAITING_APPROVAL)
    assert not base_run.approval_recorded

    # Attempt transition to BUILDING without approval
    with pytest.raises(ApprovalRequiredError):
        base_run.transition_to(RunState.BUILDING)

    # Ensure state was not modified
    assert_state(base_run, RunState.AWAITING_APPROVAL)


def test_approve_prototype_validations(base_run: Run) -> None:
    """Test approval validation rules: state check, missing ref, repeated approval."""
    # Cannot approve before AWAITING_APPROVAL
    with pytest.raises(InvalidApprovalError):
        base_run.approve_prototype(approver="lead")

    base_run.start_planning()
    base_run.finish_planning()
    base_run.submit_prototype("proto-1")

    # Valid approval
    base_run.approve_prototype(approver="lead")
    assert base_run.approval_recorded

    # Repeated approval raises error
    with pytest.raises(InvalidApprovalError) as exc_info:
        base_run.approve_prototype(approver="lead")
    assert "already been approved" in str(exc_info.value)


def test_approve_prototype_missing_ref_rejected() -> None:
    """Test that approving a run without any prototype reference fails."""
    run = Run(project_id="proj-1", state=RunState.AWAITING_APPROVAL)
    with pytest.raises(InvalidApprovalError) as exc_info:
        run.approve_prototype(approver="lead")
    assert "Missing prototype reference" in str(exc_info.value)


def test_revision_request_lifecycle(base_run: Run) -> None:
    """Test requesting prototype revisions transitions back to PROTOTYPING."""
    base_run.start_planning()
    base_run.finish_planning()
    base_run.submit_prototype("proto-v1")
    assert_state(base_run, RunState.AWAITING_APPROVAL)

    # Request revision 1
    base_run.request_revision(reason="Change primary color to Navy")
    assert_state(base_run, RunState.PROTOTYPING)
    assert base_run.revision_count == 1
    assert not base_run.approval_recorded

    # Submit prototype v2
    base_run.submit_prototype("proto-v2")
    assert_state(base_run, RunState.AWAITING_APPROVAL)

    # Request revision 2
    base_run.request_revision(reason="Add testimonials section")
    assert_state(base_run, RunState.PROTOTYPING)
    assert base_run.revision_count == 2

    # Submit prototype v3
    base_run.submit_prototype("proto-v3")
    base_run.request_revision(reason="Small copy adjustment")
    assert base_run.revision_count == 3

    # Reaching limit (max_revisions = 3)
    base_run.submit_prototype("proto-v4")
    with pytest.raises(InvalidRevisionRequestError) as exc_info:
        base_run.request_revision(reason="Another revision")
    assert "Revision limit exceeded" in str(exc_info.value)


def test_reject_approval_transitions_to_failed(base_run: Run) -> None:
    """Test that rejecting prototype approval fails the run."""
    base_run.start_planning()
    base_run.finish_planning()
    base_run.submit_prototype("proto-v1")

    base_run.reject_approval(reason="Client rejected design concept entirely.")
    assert_state(base_run, RunState.FAILED)
    assert "Client rejected design concept" in (base_run.failure_reason or "")


@pytest.mark.parametrize(
    "state",
    [
        RunState.CREATED,
        RunState.PLANNING,
        RunState.PROTOTYPING,
        RunState.AWAITING_APPROVAL,
        RunState.BUILDING,
        RunState.TESTING,
        RunState.DEPLOYING,
    ],
)
def test_failure_from_every_nonterminal_state(state: RunState) -> None:
    """Test that failure is permitted from all nonterminal states."""
    run = Run(project_id="proj-1", state=state)
    run.fail(reason="Unexpected error occurred")
    assert_state(run, RunState.FAILED)
    assert run.failure_reason == "Unexpected error occurred"


@pytest.mark.parametrize(
    "state",
    [
        RunState.CREATED,
        RunState.PLANNING,
        RunState.PROTOTYPING,
        RunState.AWAITING_APPROVAL,
        RunState.BUILDING,
        RunState.TESTING,
        RunState.DEPLOYING,
    ],
)
def test_cancellation_from_every_nonterminal_state(state: RunState) -> None:
    """Test that cancellation is permitted from all nonterminal states."""
    run = Run(project_id="proj-1", state=state)
    run.cancel(reason="Client requested stop")
    assert_state(run, RunState.CANCELLED)
    assert run.cancellation_reason == "Client requested stop"


@pytest.mark.parametrize(
    "terminal_state",
    [RunState.COMPLETED, RunState.FAILED, RunState.CANCELLED],
)
def test_terminal_states_cannot_transition(terminal_state: RunState) -> None:
    """Invariant: Terminal states cannot transition to any other state."""
    run = Run(project_id="proj-1", state=terminal_state)

    for target in RunState:
        with pytest.raises(InvalidTerminalStateOperationError):
            run.transition_to(target)

    # Terminal states cannot fail or cancel again
    with pytest.raises(InvalidTerminalStateOperationError):
        run.fail(reason="Another failure")

    with pytest.raises(InvalidTerminalStateOperationError):
        run.cancel(reason="Another cancel")


@pytest.mark.parametrize(
    "from_state,illegal_target",
    [
        (RunState.CREATED, RunState.PROTOTYPING),
        (RunState.CREATED, RunState.BUILDING),
        (RunState.CREATED, RunState.COMPLETED),
        (RunState.PLANNING, RunState.BUILDING),
        (RunState.PLANNING, RunState.CREATED),
        (RunState.PROTOTYPING, RunState.BUILDING),
        (RunState.BUILDING, RunState.DEPLOYING),
        (RunState.TESTING, RunState.COMPLETED),
        (RunState.DEPLOYING, RunState.PLANNING),
    ],
)
def test_illegal_state_transitions(
    from_state: RunState, illegal_target: RunState
) -> None:
    """Invariant: Only explicitly defined transitions are permitted."""
    run = Run(project_id="proj-1", state=from_state)
    initial_timestamp = run.updated_at

    with pytest.raises(InvalidStateTransitionError):
        run.transition_to(illegal_target)

    # Invariant: Aggregates are not partially modified on failed transitions
    assert_state(run, from_state)
    assert run.updated_at == initial_timestamp


def test_fail_qa_transitions_to_failed(base_run: Run) -> None:
    """Test that fail_qa transitions testing run to FAILED state."""
    base_run.state = RunState.TESTING
    base_run.fail_qa(reason="Security checks flagged critical vulnerability")
    assert_state(base_run, RunState.FAILED)
    assert "Security checks flagged" in (base_run.failure_reason or "")


def test_empty_failure_reason_rejected(base_run: Run) -> None:
    """Invariant: Failure transition requires a meaningful failure reason."""
    with pytest.raises(DomainInvariantError):
        base_run.fail(reason="")

    with pytest.raises(DomainInvariantError):
        base_run.fail(reason="   ")
