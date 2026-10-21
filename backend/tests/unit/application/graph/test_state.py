"""Unit tests for workflow state schema and initialization."""

import pytest
from pydantic import ValidationError

from agency.application.graph.state import (
    WorkflowStateModel,
    init_workflow_state,
)
from agency.domain.entities.brief import Brief


def _make_brief() -> Brief:
    return Brief(
        client_name="Kaelen Thorne",
        site_type="Systems Architecture Portfolio",
        pages=["Home", "About", "Projects", "Contact"],
        tone="Technical and refined",
        content_notes="Distributed systems specialist with 10 years experience.",
    )


def test_init_workflow_state_initializes_defaults() -> None:
    """init_workflow_state initializes a clean, well-formed state dictionary."""
    brief = _make_brief()
    state = init_workflow_state(brief=brief)

    assert state["run_id"]
    assert state["project_id"] == "kaelen-thorne"
    assert state["brief"]["client_name"] == "Kaelen Thorne"
    assert state["approval_status"] == "pending"
    assert state["approval_revision"] == 0
    assert state["repair_attempts"] == 0
    assert state["cancel_requested"] is False
    assert state["current_stage"] == "initialized"
    assert state["spec"] is None
    assert state["clarification_questions"] == []


def test_init_workflow_state_custom_ids() -> None:
    """Explicit run_id and project_id are honored."""
    brief = _make_brief()
    state = init_workflow_state(
        brief=brief,
        project_id="custom-project",
        run_id="run-custom-123",
    )

    assert state["run_id"] == "run-custom-123"
    assert state["project_id"] == "custom-project"


def test_workflow_state_model_validates_valid_dict() -> None:
    """WorkflowStateModel successfully validates initialized state."""
    brief = _make_brief()
    state = init_workflow_state(brief=brief)
    model = WorkflowStateModel.model_validate(state)

    assert model.run_id == state["run_id"]
    assert model.project_id == state["project_id"]
    assert model.repair_attempts == 0


def test_workflow_state_model_rejects_missing_required_fields() -> None:
    """WorkflowStateModel rejects missing mandatory run_id or brief."""
    with pytest.raises(ValidationError):
        WorkflowStateModel.model_validate({"project_id": "test"})
