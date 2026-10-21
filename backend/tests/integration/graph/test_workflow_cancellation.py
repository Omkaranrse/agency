"""Integration test: Workflow cancellation before and during approval gate."""

from tests.integration.graph.conftest import build_test_harness, make_test_brief

from agency.domain.enums import RunState
from agency.infrastructure.persistence import create_in_memory_checkpointer


def test_workflow_cancellation_during_approval_gate() -> None:
    """Cancelling a workflow waiting at the approval gate terminates it cleanly."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()

    # 1. Start workflow to preview / await_approval gate
    harness.service.start_workflow(
        brief=brief,
        run_id="run-cancel-1",
    )

    # 2. Request cancellation
    cancelled_state = harness.service.request_cancellation(
        run_id="run-cancel-1",
        reason="Client terminated contract.",
    )

    # 3. Verify graph reached cancel stage
    assert cancelled_state["current_stage"] == "cancel"
    assert cancelled_state["cancel_requested"] is True
    assert "Client terminated" in (cancelled_state.get("cancellation_reason") or "")

    # 4. Verify build and deploy were never executed
    assert cancelled_state["build_result"] is None
    assert cancelled_state["deployment_result"] is None
    assert len(harness.deploy.calls) == 0

    # 5. Verify domain aggregate reached CANCELLED
    run = harness.repository.get_by_id("run-cancel-1")
    assert run is not None
    assert run.state == RunState.CANCELLED
    assert "Client terminated" in (run.cancellation_reason or "")


def test_workflow_cancellation_before_approval() -> None:
    """A run cancelled immediately after intake does not proceed through planning."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    brief = make_test_brief()
    run_id = "run-cancel-early"

    # Start and immediately mark cancel intent
    paused_state = harness.service.start_workflow(
        brief=brief,
        run_id=run_id,
    )
    assert paused_state["current_stage"] == "preview"
    # Cancel at approval pause
    res = harness.service.request_cancellation(run_id, reason="Aborted by admin")

    assert res["current_stage"] == "cancel"
    run = harness.repository.get_by_id(run_id)
    assert run is not None
    assert run.state == RunState.CANCELLED
