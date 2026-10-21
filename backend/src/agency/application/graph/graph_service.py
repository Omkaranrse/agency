"""High-level application service for orchestrating durable workflow executions."""

import logging
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from agency.application.errors import RunNotFoundError
from agency.application.graph.approval import (
    ApprovalDecision,
    validate_approval_decision,
)
from agency.application.graph.builder import WorkflowGraphBuilder
from agency.application.graph.errors import (
    ApprovalValidationError,
    GraphExecutionError,
)
from agency.application.graph.nodes import GraphNodes
from agency.application.graph.state import WorkflowState, init_workflow_state
from agency.domain.entities.brief import Brief
from agency.domain.entities.run import Run

logger = logging.getLogger(__name__)


class WorkflowGraphService:
    """Coordinates execution, resumption, and inspection of durable Agency runs."""

    def __init__(
        self,
        nodes: GraphNodes,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
    ) -> None:
        self.nodes = nodes
        self.checkpointer = checkpointer
        builder = WorkflowGraphBuilder(nodes=nodes, checkpointer=checkpointer)
        self.graph: CompiledStateGraph[Any, Any, Any, Any] = builder.build()

    @staticmethod
    def _make_config(run_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": run_id}}

    def start_workflow(
        self,
        brief: Brief,
        project_id: str | None = None,
        run_id: str | None = None,
    ) -> WorkflowState:
        """Initialize and begin execution of a durable Agency multi-agent workflow."""
        initial_state = init_workflow_state(
            brief=brief,
            project_id=project_id,
            run_id=run_id,
        )
        resolved_run_id = initial_state["run_id"]
        self.nodes.tracing.start_trace(
            run_id=resolved_run_id,
            name="agency.workflow",
            metadata={
                "project_id": initial_state.get("project_id"),
                "site_type": brief.site_type,
                "client_name": brief.client_name,
            },
        )
        config = self._make_config(resolved_run_id)

        result = self.graph.invoke(initial_state, config=config)
        return self._extract_clean_state(result)

    def submit_approval(
        self,
        run_id: str,
        decision: ApprovalDecision,
    ) -> WorkflowState:
        """Submit an explicit human approval, revision, or rejection decision."""
        config = self._make_config(run_id)
        current = self.graph.get_state(config)

        if not current or not current.values:
            raise RunNotFoundError(run_id)

        current_values = current.values
        current_revision = current_values.get("approval_revision", 0)

        # Invariant checks before resumption
        validate_approval_decision(decision, current_revision=current_revision)

        # Check if awaiting approval
        if not current.next:
            raise ApprovalValidationError(
                f"Run '{run_id}' is not currently paused at a gate."
            )

        cmd: Command[Any] = Command(resume=decision.model_dump(mode="json"))
        result = self.graph.invoke(cmd, config=config)
        return self._extract_clean_state(result)

    def submit_clarification(
        self,
        run_id: str,
        answers: dict[str, str],
    ) -> WorkflowState:
        """Submit client answers to clarification questions and resume analysis."""
        config = self._make_config(run_id)
        current = self.graph.get_state(config)

        if not current or not current.values:
            raise RunNotFoundError(run_id)

        if not current.next:
            raise GraphExecutionError(
                f"Run '{run_id}' is not paused for clarification."
            )

        cmd: Command[Any] = Command(resume=answers)
        result = self.graph.invoke(cmd, config=config)
        return self._extract_clean_state(result)

    def request_cancellation(
        self,
        run_id: str,
        reason: str = "Cancelled by user",
    ) -> WorkflowState:
        """Request immediate cancellation of an active or interrupted workflow run."""
        config = self._make_config(run_id)
        current = self.graph.get_state(config)

        if not current or not current.values:
            raise RunNotFoundError(run_id)

        # Update checkpointed state with cancellation intent
        self.graph.update_state(
            config,
            {"cancel_requested": True, "cancellation_reason": reason},
        )

        # If currently paused at an interrupt, resume to let cancel node execute
        if current.next:
            revision = current.values.get("approval_revision", 0)
            resume_payload = {
                "decision": "reject",
                "comment": f"Cancelled: {reason}",
                "revision": revision,
            }
            cmd: Command[Any] = Command(resume=resume_payload)
            result = self.graph.invoke(cmd, config=config)
            return self._extract_clean_state(result)

        # If not paused, verify repository aggregate is cancelled
        run = self.nodes.repository.get_by_id(run_id)
        if run and run.state not in Run.TERMINAL_STATES:
            run.cancel(reason=reason)
            self.nodes.repository.save(run)
            self.nodes.event_bus.publish_all(run.clear_events())

        updated = self.graph.get_state(config)
        return self._extract_clean_state(updated.values)

    def get_state(self, run_id: str) -> WorkflowState:
        """Retrieve the latest checkpointed workflow state for a given run ID."""
        config = self._make_config(run_id)
        state_snapshot = self.graph.get_state(config)
        if not state_snapshot or not state_snapshot.values:
            raise RunNotFoundError(run_id)
        return self._extract_clean_state(state_snapshot.values)

    def get_state_history(self, run_id: str) -> list[WorkflowState]:
        """Retrieve chronological checkpoint snapshots for auditing and recovery."""
        config = self._make_config(run_id)
        snapshots = self.graph.get_state_history(config)
        return [self._extract_clean_state(s.values) for s in snapshots if s.values]

    @staticmethod
    def _extract_clean_state(raw: Any) -> WorkflowState:
        """Strip internal LangGraph metadata keys from user-facing state dict."""
        if not isinstance(raw, dict):
            return {}
        cleaned = {k: v for k, v in raw.items() if not str(k).startswith("__")}
        return cast(WorkflowState, cleaned)
