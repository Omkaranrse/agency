"""Integration test: Automated QA failure triggering repair loop and recovery."""

from tests.fakes.fake_qa_service import make_failing_qa_report, make_passing_qa_report
from tests.integration.graph.conftest import build_test_harness, make_test_brief

from agency.application.graph.approval import ApprovalDecision, ApprovalDecisionType
from agency.domain.enums import RunState
from agency.infrastructure.persistence import create_in_memory_checkpointer


def test_workflow_qa_repair_loop_recovers_and_deploys() -> None:
    """QA failure triggers Builder repair, builds again, passes QA, and deploys."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    # 1. Enqueue 1 QA failure followed by 1 QA pass
    failing_report = make_failing_qa_report(failing_checks=["accessibility"])
    passing_report = make_passing_qa_report()
    harness.qa_service.enqueue_report(failing_report)
    harness.qa_service.enqueue_report(passing_report)

    brief = make_test_brief()

    # 2. Start workflow and pause at approval
    harness.service.start_workflow(
        brief=brief,
        run_id="run-repair-1",
    )

    # 3. Approve prototype
    decision = ApprovalDecision(
        decision=ApprovalDecisionType.APPROVE,
        revision=0,
    )
    final_state = harness.service.submit_approval("run-repair-1", decision)

    # 4. Verify repair cycle occurred and workflow reached handover
    assert final_state["repair_attempts"] == 1
    assert final_state["current_stage"] == "handover"
    assert final_state["deployment_result"] is not None

    # 5. Verify domain aggregate reached COMPLETED
    run = harness.repository.get_by_id("run-repair-1")
    assert run is not None
    assert run.state == RunState.COMPLETED
