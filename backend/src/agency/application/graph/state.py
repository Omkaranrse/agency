"""Typed workflow state contracts and boundary models for LangGraph."""

import uuid
from typing import Any, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from agency.domain.entities.brief import Brief


class WorkflowState(TypedDict, total=False):
    """Mutable typed dictionary representing graph state across node boundaries."""

    run_id: str
    project_id: str
    brief: dict[str, Any]
    spec: dict[str, Any] | None
    clarification_questions: list[str]
    clarification_answers: dict[str, str] | None
    design_tokens: dict[str, Any] | None
    page_content: list[dict[str, Any]] | None
    preview_result: dict[str, Any] | None
    approval_status: str | None
    approval_revision: int
    approval_comment: str | None
    approval_approver: str | None
    build_result: dict[str, Any] | None
    qa_report: dict[str, Any] | None
    repair_attempts: int
    deployment_result: dict[str, Any] | None
    handover_report: dict[str, Any] | None
    current_stage: str
    cancel_requested: bool
    cancellation_reason: str | None
    failure_code: str | None
    failure_message: str | None
    prompt_versions: dict[str, str]
    artifact_references: list[str]
    sandbox_id: str | None


class WorkflowStateModel(BaseModel):
    """Pydantic validated representation of WorkflowState for invariant checks."""

    model_config = ConfigDict(extra="ignore")

    run_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    brief: dict[str, Any]
    spec: dict[str, Any] | None = None
    clarification_questions: list[str] = Field(default_factory=list)
    clarification_answers: dict[str, str] | None = None
    design_tokens: dict[str, Any] | None = None
    page_content: list[dict[str, Any]] | None = None
    preview_result: dict[str, Any] | None = None
    approval_status: str | None = None
    approval_revision: int = Field(default=0, ge=0)
    approval_comment: str | None = None
    approval_approver: str | None = None
    build_result: dict[str, Any] | None = None
    qa_report: dict[str, Any] | None = None
    repair_attempts: int = Field(default=0, ge=0, le=10)
    deployment_result: dict[str, Any] | None = None
    handover_report: dict[str, Any] | None = None
    current_stage: str = "initialized"
    cancel_requested: bool = False
    cancellation_reason: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    artifact_references: list[str] = Field(default_factory=list)
    sandbox_id: str | None = None


def init_workflow_state(
    brief: Brief,
    project_id: str | None = None,
    run_id: str | None = None,
) -> WorkflowState:
    """Initialize a clean, deterministic WorkflowState from a validated client Brief."""
    resolved_run_id = run_id or str(uuid.uuid4())
    resolved_project_id = project_id or brief.client_name.lower().replace(" ", "-")

    return {
        "run_id": resolved_run_id,
        "project_id": resolved_project_id,
        "brief": brief.model_dump(mode="json"),
        "spec": None,
        "clarification_questions": [],
        "clarification_answers": None,
        "design_tokens": None,
        "page_content": None,
        "preview_result": None,
        "approval_status": "pending",
        "approval_revision": 0,
        "approval_comment": None,
        "approval_approver": None,
        "build_result": None,
        "qa_report": None,
        "repair_attempts": 0,
        "deployment_result": None,
        "handover_report": None,
        "current_stage": "initialized",
        "cancel_requested": False,
        "cancellation_reason": None,
        "failure_code": None,
        "failure_message": None,
        "prompt_versions": {},
        "artifact_references": [],
        "sandbox_id": None,
    }
