"""Integration test: Prototype rejection terminating workflow without build."""

from tests.integration.graph.conftest import build_test_harness, make_test_brief

from agency.application.graph.approval import ApprovalDecision, ApprovalDecisionType
from agency.domain.enums import RunState
from agency.infrastructure.persistence import create_in_memory_checkpointer


def test_workflow_rejection_terminates_in_failure() -> None:
    """Approval rejection halts execution; build and deploy are never called."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()

    # 1. Start workflow to preview gate
    harness.service.start_workflow(
        brief=brief,
        run_id="run-reject-1",
    )

    # 2. Submit rejection decision
    rejection = ApprovalDecision(
        decision=ApprovalDecisionType.REJECT,
        revision=0,
        comment="Design direction does not match client aesthetic.",
    )
    rejected_state = harness.service.submit_approval("run-reject-1", rejection)

    # 3. Verify terminal failure state
    assert rejected_state["current_stage"] == "fail"
    assert rejected_state["approval_status"] == "rejected"
    assert rejected_state["failure_code"] == "APPROVAL_REJECTED"

    # 4. Verify build and deploy were never executed
    assert rejected_state["build_result"] is None
    assert rejected_state["deployment_result"] is None
    assert len(harness.deploy.calls) == 0

    # 5. Verify domain aggregate state is FAILED
    run = harness.repository.get_by_id("run-reject-1")
    assert run is not None
    assert run.state == RunState.FAILED
    assert "Design direction does not match" in (run.failure_reason or "")
