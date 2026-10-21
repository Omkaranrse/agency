"""Integration test: Human approval revision loops and stale approval protection."""

import pytest
from tests.integration.graph.conftest import build_test_harness, make_test_brief

from agency.application.graph.approval import ApprovalDecision, ApprovalDecisionType
from agency.application.graph.errors import StaleApprovalError
from agency.infrastructure.persistence import create_in_memory_checkpointer


def test_workflow_revision_loop_and_stale_approval_blocking() -> None:
    """Revision requests increment revision, update preview, block stale approvals."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()

    # 1. Start workflow to initial approval gate (revision 0)
    initial_state = harness.service.start_workflow(
        brief=brief,
        run_id="run-revise-1",
    )
    assert initial_state["current_stage"] == "preview"
    assert initial_state["approval_revision"] == 0

    # 2. Submit revision request
    revision_decision = ApprovalDecision(
        decision=ApprovalDecisionType.REVISE,
        revision=0,
        comment="Adjust color contrast for warmer terracotta tone.",
    )
    revised_state = harness.service.submit_approval("run-revise-1", revision_decision)

    # 3. Verify graph looped back to designer & preview with revision 1
    assert revised_state["current_stage"] == "preview"
    assert revised_state["approval_revision"] == 1
    assert revised_state["approval_status"] == "pending"
    assert revised_state["preview_result"] is not None
    assert "rev1" in str(revised_state["preview_result"]["preview_ref"])

    # 4. Attempt to approve using stale revision 0 -> must be rejected
    stale_decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=0,
        approver="client",
    )
    with pytest.raises(StaleApprovalError, match="Stale approval decision"):
        harness.service.submit_approval("run-revise-1", stale_decision)

    # 5. Submit valid approval for current revision 1
    valid_decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=1,
        approver="client",
    )
    completed_state = harness.service.submit_approval("run-revise-1", valid_decision)

    # 6. Verify run finishes deployment
    assert completed_state["current_stage"] == "handover"
    assert completed_state["approval_status"] == "approved"
    assert completed_state["approval_revision"] == 1
