"""Unit tests for explicit workflow conditional routing functions."""

from agency.application.graph.routing import (
    route_after_approval,
    route_after_build,
    route_after_clarification,
    route_after_deploy,
    route_after_designer,
    route_after_intake,
    route_after_pm_spec,
    route_after_preview,
    route_after_qa,
    route_after_repair,
)
from agency.application.graph.state import WorkflowState


def test_route_after_intake() -> None:
    """Test intake routing with normal, cancel, and failure conditions."""
    assert route_after_intake({"cancel_requested": False}) == "pm_spec"
    assert route_after_intake({"cancel_requested": True}) == "cancel"
    assert route_after_intake({"failure_code": "ERR"}) == "fail"


def test_route_after_pm_spec() -> None:
    """Test pm_spec routing for clarification vs designer."""
    state_normal: WorkflowState = {"clarification_questions": []}
    assert route_after_pm_spec(state_normal) == "designer"

    state_clarify: WorkflowState = {
        "clarification_questions": ["What is your background?"]
    }
    assert route_after_pm_spec(state_clarify) == "await_clarification"

    state_cancel: WorkflowState = {"cancel_requested": True}
    assert route_after_pm_spec(state_cancel) == "cancel"


def test_route_after_clarification() -> None:
    """Test clarification routing returns to pm_spec."""
    assert route_after_clarification({}) == "pm_spec"
    assert route_after_clarification({"cancel_requested": True}) == "cancel"


def test_route_after_designer() -> None:
    """Test designer routing to preview."""
    assert route_after_designer({}) == "preview"
    assert route_after_designer({"cancel_requested": True}) == "cancel"


def test_route_after_preview() -> None:
    """Test preview routing to await_approval."""
    assert route_after_preview({}) == "await_approval"
    assert route_after_preview({"cancel_requested": True}) == "cancel"


def test_route_after_approval() -> None:
    """Test approval routing for approve, revise, and reject."""
    assert route_after_approval({"approval_status": "approved"}) == "build"
    assert route_after_approval({"approval_status": "revised"}) == "designer"
    assert route_after_approval({"approval_status": "rejected"}) == "fail"
    assert (
        route_after_approval({"approval_status": "approved", "cancel_requested": True})
        == "cancel"
    )


def test_route_after_build() -> None:
    """Test build routing to qa on success, fail on failure."""
    assert (
        route_after_build({"build_result": {"success": True, "exit_code": 0}}) == "qa"
    )
    assert (
        route_after_build({"build_result": {"success": False, "exit_code": 1}})
        == "fail"
    )
    assert route_after_build({"cancel_requested": True}) == "cancel"


def test_route_after_qa() -> None:
    """Test QA routing: deploy on pass, repair on retries, fail on exhaustion."""
    assert (
        route_after_qa({"qa_report": {"overall_passed": True}, "repair_attempts": 0})
        == "deploy"
    )

    # First and second QA failure -> repair
    assert (
        route_after_qa({"qa_report": {"overall_passed": False}, "repair_attempts": 0})
        == "repair"
    )
    assert (
        route_after_qa({"qa_report": {"overall_passed": False}, "repair_attempts": 2})
        == "repair"
    )

    # Third failure -> exhausted -> fail
    assert (
        route_after_qa({"qa_report": {"overall_passed": False}, "repair_attempts": 3})
        == "fail"
    )
    assert route_after_qa({"cancel_requested": True}) == "cancel"


def test_route_after_repair() -> None:
    """Test repair routing returns to build."""
    assert route_after_repair({}) == "build"
    assert route_after_repair({"cancel_requested": True}) == "cancel"


def test_route_after_deploy() -> None:
    """Test deploy routing to handover."""
    assert route_after_deploy({}) == "handover"
    assert route_after_deploy({"failure_code": "DEPLOY_FAILED"}) == "fail"
