"""Integration test: End-to-end happy path workflow execution."""

from tests.integration.graph.conftest import build_test_harness, make_test_brief

from agency.application.graph.approval import ApprovalDecision, ApprovalDecisionType
from agency.domain.enums import RunState
from agency.infrastructure.persistence import create_in_memory_checkpointer


def test_workflow_happy_path_completes_successfully() -> None:
    """Full workflow runs from brief to production deployment and handover."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()

    # 1. Start workflow - should advance to await_approval interrupt
    paused_state = harness.service.start_workflow(
        brief=brief,
        run_id="run-happy-1",
        project_id="elena-rostova",
    )

    assert paused_state["current_stage"] == "preview"
    assert paused_state["approval_status"] == "pending"
    assert paused_state["preview_result"] is not None
    assert paused_state["spec"] is not None
    assert paused_state["design_tokens"] is not None

    # Verify domain Run aggregate transitioned to AWAITING_APPROVAL
    run_awaiting = harness.repository.get_by_id("run-happy-1")
    assert run_awaiting is not None
    assert run_awaiting.state == RunState.AWAITING_APPROVAL

    # 2. Submit human approval
    decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=0,
        approver="client-elena",
    )
    completed_state = harness.service.submit_approval("run-happy-1", decision)

    # 3. Verify terminal stage and outputs
    assert completed_state["current_stage"] == "handover"
    assert completed_state["approval_status"] == "approved"
    assert completed_state["deployment_result"] is not None
    assert "https://elena-rostova-preview.agency.run" in str(
        completed_state["deployment_result"]["preview_url"]
    )
    assert completed_state["handover_report"] is not None
    assert completed_state["handover_report"]["qa_status"] == "passed"
    assert completed_state["handover_report"]["build_status"] == "success"

    # 4. Verify domain aggregate reached terminal COMPLETED state
    run_completed = harness.repository.get_by_id("run-happy-1")
    assert run_completed is not None
    assert run_completed.state == RunState.COMPLETED
    assert run_completed.approval_recorded is True
    assert run_completed.approver == "client-elena"
