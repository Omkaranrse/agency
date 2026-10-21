"""Integration test: Bounded QA repair cycle exhaustion terminating in failure."""

from tests.fakes.fake_qa_service import make_failing_qa_report
from tests.integration.graph.conftest import build_test_harness, make_test_brief

from agency.application.graph.approval import ApprovalDecision, ApprovalDecisionType
from agency.domain.enums import RunState
from agency.infrastructure.persistence import create_in_memory_checkpointer


def test_workflow_qa_exhaustion_terminates_without_deploy() -> None:
    """Repeated QA failures execute exactly 3 repairs then terminate in FAILED state."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    # 1. Enqueue 4 consecutive QA failures (initial + 3 repair loops)
    for _ in range(4):
        harness.qa_service.enqueue_report(
            make_failing_qa_report(failing_checks=["lighthouse", "accessibility"])
        )

    brief = make_test_brief()

    # 2. Start workflow and pause at approval
    harness.service.start_workflow(
        brief=brief,
        run_id="run-exhaust-1",
    )

    # 3. Approve prototype
    decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=0,
    )
    final_state = harness.service.submit_approval("run-exhaust-1", decision)

    # 4. Verify exactly 3 repairs executed and stage failed
    assert final_state["current_stage"] == "fail"
    assert final_state["repair_attempts"] == 3
    assert final_state["failure_code"] == "QA_EXHAUSTED"
    assert "QA checks failed after 3 repair attempts" in (
        final_state.get("failure_message") or ""
    )

    # 5. Verify deploy was never called
    assert final_state["deployment_result"] is None
    assert len(harness.deploy.calls) == 0

    # 6. Verify domain aggregate reached FAILED state
    run = harness.repository.get_by_id("run-exhaust-1")
    assert run is not None
    assert run.state == RunState.FAILED
    assert "QA checks failed" in (run.failure_reason or "")
