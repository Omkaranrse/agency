"""Integration tests: Failure recovery and side-effect idempotency."""

import pytest
from tests.integration.graph.conftest import build_test_harness, make_test_brief

from agency.application.graph.approval import ApprovalDecision, ApprovalDecisionType
from agency.application.graph.errors import ApprovalValidationError, StaleApprovalError
from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.infrastructure.persistence import create_in_memory_checkpointer


def test_deployment_failure_produces_explicit_error_without_inventing_success() -> None:
    """When deploy provider raises an error, workflow fails explicitly."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()
    harness.service.start_workflow(
        brief=brief,
        run_id="run-deploy-fail-1",
        project_id="elena-fail",
    )

    # Configure external deploy provider failure before side effect
    harness.deploy.set_failure(RuntimeError("Cloud provider 503 Service Unavailable"))

    decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=0,
        approver="client-elena",
    )
    final_state = harness.service.submit_approval("run-deploy-fail-1", decision)

    # Verify failure is recorded explicitly and terminal fail node reached
    assert final_state["current_stage"] == "fail"
    assert final_state.get("failure_code") == "DEPLOYMENT_FAILED"
    assert "Cloud provider 503" in str(final_state.get("failure_message"))
    assert final_state.get("deployment_result") is None

    # Verify domain entity transitioned to FAILED rather than COMPLETED
    run = harness.repository.get_by_id("run-deploy-fail-1")
    assert run is not None
    assert run.state == RunState.FAILED


def test_idempotent_deploy_prevents_duplicate_external_calls() -> None:
    """Deploy node with existing result does not duplicate side effects."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()
    harness.service.start_workflow(
        brief=brief,
        run_id="run-idempotent-deploy-1",
        project_id="elena-idempotent",
    )

    decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=0,
        approver="client-elena",
    )
    completed_state = harness.service.submit_approval(
        "run-idempotent-deploy-1", decision
    )

    assert completed_state["current_stage"] == "handover"
    assert len(harness.deploy.calls) == 1

    # Simulate re-running deploy node directly with the existing completed state
    node_out = harness.nodes.deploy(completed_state)

    # Verify node returned existing deployment result without calling provider again
    assert len(harness.deploy.calls) == 1
    assert node_out["deployment_result"] == completed_state["deployment_result"]


def test_intake_reuses_existing_run_aggregate_without_error() -> None:
    """If Run already exists in repository, intake reuses it rather than duplicating."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()
    existing_run = Run(
        run_id="run-pre-existing-1",
        project_id="elena-pre-existing",
        brief=brief,
    )
    existing_run.start_planning()
    harness.repository.save(existing_run)

    # Start workflow for existing run_id
    paused_state = harness.service.start_workflow(
        brief=brief,
        run_id="run-pre-existing-1",
        project_id="elena-pre-existing",
    )

    # Should succeed without failing or creating collision
    assert paused_state["current_stage"] == "preview"
    reloaded_run = harness.repository.get_by_id("run-pre-existing-1")
    assert reloaded_run is not None
    assert reloaded_run.state == RunState.AWAITING_APPROVAL


def test_stale_approval_and_redundant_resumption_rejected() -> None:
    """Approval cannot be submitted twice or with stale revision."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()
    harness.service.start_workflow(
        brief=brief,
        run_id="run-idempotent-approval-1",
        project_id="elena-approval",
    )

    # Request revision to bump revision to 1
    revise_decision = ApprovalDecision(
        decision=ApprovalDecisionType.REVISE,
        revision=0,
        comment="Change color theme",
    )
    revised_state = harness.service.submit_approval(
        "run-idempotent-approval-1", revise_decision
    )
    assert revised_state["approval_revision"] == 1

    # Attempting to submit approval with stale revision 0 must fail
    stale_decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=0,
        approver="client-elena",
    )
    with pytest.raises(StaleApprovalError):
        harness.service.submit_approval("run-idempotent-approval-1", stale_decision)

    # Submit valid approval for revision 1
    valid_decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=1,
        approver="client-elena",
    )
    completed_state = harness.service.submit_approval(
        "run-idempotent-approval-1", valid_decision
    )
    assert completed_state["current_stage"] == "handover"

    # Redundant resume on already finished workflow raises ApprovalValidationError
    with pytest.raises(ApprovalValidationError):
        harness.service.submit_approval("run-idempotent-approval-1", valid_decision)
