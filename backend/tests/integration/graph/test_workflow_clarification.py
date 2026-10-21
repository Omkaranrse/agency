"""Integration test: Client clarification workflow pause and resumption."""

from tests.integration.graph.conftest import (
    build_test_harness,
    make_test_brief,
    make_test_spec,
)

from agency.application.agents.models import PMOutputSchema
from agency.infrastructure.persistence import create_in_memory_checkpointer


def test_workflow_stops_for_clarification_and_resumes() -> None:
    """PM agent identifies missing info, pauses, and resumes after clarification."""
    checkpointer = create_in_memory_checkpointer()
    harness = build_test_harness(checkpointer=checkpointer)

    # 1. Configure PMAgent to first request clarification
    harness.fake_llm.set_response(
        PMOutputSchema,
        PMOutputSchema(
            needs_clarification=True,
            clarification_questions=[
                "Which specific engineering projects should be featured?"
            ],
            missing_fields=["featured_projects"],
        ),
    )

    brief = make_test_brief()

    # 2. Start workflow - must pause at await_clarification interrupt
    paused_state = harness.service.start_workflow(
        brief=brief,
        run_id="run-clarify-1",
    )

    assert paused_state["current_stage"] == "pm_clarification"
    assert len(paused_state["clarification_questions"]) == 1
    assert "featured" in paused_state["clarification_questions"][0].lower()
    # Ensure designer, build, deploy stages were never entered
    assert paused_state["spec"] is None
    assert paused_state["design_tokens"] is None
    assert paused_state["build_result"] is None

    # 3. Configure PMAgent to return valid spec once clarification is answered
    sample_spec = make_test_spec()
    harness.fake_llm.set_response(
        PMOutputSchema,
        PMOutputSchema(spec=sample_spec),
    )

    # 4. Submit clarification answers
    answers = {
        "featured_projects": "Include Mass Timber Civic Center and Green Highrise."
    }
    resumed_state = harness.service.submit_clarification(
        run_id="run-clarify-1",
        answers=answers,
    )

    # 5. Verify workflow resumed and progressed to preview gate
    assert resumed_state["current_stage"] == "preview"
    assert resumed_state["approval_status"] == "pending"
    assert resumed_state["spec"] is not None
    assert resumed_state["design_tokens"] is not None
    assert len(resumed_state["clarification_questions"]) == 0
