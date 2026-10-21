"""Integration test: Recovery after process restart using SQLite checkpoints."""

import tempfile
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from tests.integration.graph.conftest import build_test_harness, make_test_brief

from agency.application.graph.approval import ApprovalDecision, ApprovalDecisionType
from agency.domain.enums import RunState


def test_workflow_recovers_across_process_restart() -> None:
    """A paused approval workflow resumes cleanly from disk across service instances."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "checkpoints.db")
        run_id = "run-restart-test-101"
        brief = make_test_brief()

        # ==========================================
        # Process 1: Start workflow until approval interrupt
        # ==========================================
        with SqliteSaver.from_conn_string(db_path) as checkpointer1:
            harness1 = build_test_harness(checkpointer=checkpointer1)
            paused_state = harness1.service.start_workflow(
                brief=brief,
                run_id=run_id,
                project_id="elena-rostova",
            )
            assert paused_state["current_stage"] == "preview"
            assert paused_state["approval_status"] == "pending"
            assert paused_state["approval_revision"] == 0
            assert paused_state["spec"] is not None
            assert paused_state["design_tokens"] is not None

            # Persist domain run state across simulated process boundary
            run1 = harness1.repository.get_by_id(run_id)
            assert run1 is not None
            assert run1.state == RunState.AWAITING_APPROVAL

        # Process 1 is closed; connections and in-memory caches are torn down.

        # ==========================================
        # Process 2: Reconstruct graph from SQLite DB file and resume
        # ==========================================
        with SqliteSaver.from_conn_string(db_path) as checkpointer2:
            harness2 = build_test_harness(checkpointer=checkpointer2)
            # Rehydrate repository with domain run state from process 1
            if run1 is not None:
                harness2.repository.save(run1)

            # Inspect recovered checkpoint state
            recovered_state = harness2.service.get_state(run_id)
            assert recovered_state["current_stage"] == "preview"
            assert recovered_state["approval_status"] == "pending"
            assert recovered_state["approval_revision"] == 0
            assert recovered_state["spec"] is not None

            # Submit human approval in new process
            decision = ApprovalDecision(
                decision=ApprovalDecisionType.APPROVE,
                revision=0,
                approver="elena-client",
            )
            completed_state = harness2.service.submit_approval(run_id, decision)

            # Verify completion
            assert completed_state["current_stage"] == "handover"
            assert completed_state["approval_status"] == "approved"
            assert completed_state["deployment_result"] is not None
            assert completed_state["handover_report"] is not None

            # Verify domain aggregate
            run2 = harness2.repository.get_by_id(run_id)
            assert run2 is not None
            assert run2.state == RunState.COMPLETED
