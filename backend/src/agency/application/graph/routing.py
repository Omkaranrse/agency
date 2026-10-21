"""Explicit conditional routing logic for workflow state machine transitions."""

from agency.application.graph.state import WorkflowState

MAX_REPAIR_CYCLES = 3


def route_after_intake(state: WorkflowState) -> str:
    """Route from intake node based on cancellation or success."""
    if state.get("cancel_requested"):
        return "cancel"
    if state.get("failure_code"):
        return "fail"
    return "pm_spec"


def route_after_pm_spec(state: WorkflowState) -> str:
    """Route from pm_spec node: clarification, failure, cancellation, or designer."""
    if state.get("cancel_requested"):
        return "cancel"
    if state.get("failure_code"):
        return "fail"
    if state.get("clarification_questions"):
        return "await_clarification"
    return "designer"


def route_after_clarification(state: WorkflowState) -> str:
    """Route from await_clarification node back to pm_spec for re-evaluation."""
    if state.get("cancel_requested"):
        return "cancel"
    if state.get("failure_code"):
        return "fail"
    return "pm_spec"


def route_after_designer(state: WorkflowState) -> str:
    """Route from designer node to preview or terminal failure."""
    if state.get("cancel_requested"):
        return "cancel"
    if state.get("failure_code"):
        return "fail"
    return "preview"


def route_after_preview(state: WorkflowState) -> str:
    """Route from preview node to human approval gate."""
    if state.get("cancel_requested"):
        return "cancel"
    if state.get("failure_code"):
        return "fail"
    return "await_approval"


def route_after_approval(state: WorkflowState) -> str:
    """Route from await_approval node based on human decision."""
    if state.get("cancel_requested"):
        return "cancel"

    status = state.get("approval_status")
    if status == "approved":
        return "build"
    if status == "revised":
        return "designer"
    if status == "rejected":
        return "fail"

    return "fail"


def route_after_build(state: WorkflowState) -> str:
    """Route from build node to QA or fail on compilation/execution errors."""
    if state.get("cancel_requested"):
        return "cancel"

    build_res = state.get("build_result") or {}
    if not build_res.get("success", False) or state.get("failure_code"):
        return "fail"

    return "qa"


def route_after_qa(state: WorkflowState) -> str:
    """Route from QA node: deploy on pass, repair on fail, or fail when exhausted."""
    if state.get("cancel_requested"):
        return "cancel"

    qa_report = state.get("qa_report") or {}
    if qa_report.get("overall_passed", False):
        return "deploy"

    # Evaluate repair cycles bound
    repair_attempts = state.get("repair_attempts", 0)
    if repair_attempts < MAX_REPAIR_CYCLES:
        return "repair"

    return "fail"


def route_after_repair(state: WorkflowState) -> str:
    """Route from repair node back to build stage for compilation."""
    if state.get("cancel_requested"):
        return "cancel"
    if state.get("failure_code"):
        return "fail"
    return "build"


def route_after_deploy(state: WorkflowState) -> str:
    """Route from deploy node to handover report generation or fail."""
    if state.get("failure_code"):
        return "fail"
    return "handover"
