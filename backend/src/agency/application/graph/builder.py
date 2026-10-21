"""Graph builder constructing and compiling the durable Agency workflow."""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agency.application.graph.nodes import GraphNodes
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


class WorkflowGraphBuilder:
    """Constructs and compiles the multi-agent delivery StateGraph with checkpoints."""

    def __init__(
        self,
        nodes: GraphNodes,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
    ) -> None:
        self.nodes = nodes
        self.checkpointer = checkpointer

    def build(self) -> CompiledStateGraph[Any, Any, Any, Any]:
        """Construct the complete state machine with explicit typed transitions."""
        builder = StateGraph(WorkflowState)

        # 1. Register all nodes
        builder.add_node("intake", self.nodes.intake)
        builder.add_node("pm_spec", self.nodes.pm_spec)
        builder.add_node("await_clarification", self.nodes.await_clarification)
        builder.add_node("designer", self.nodes.designer)
        builder.add_node("preview", self.nodes.preview)
        builder.add_node("await_approval", self.nodes.await_approval)
        builder.add_node("build", self.nodes.build)
        builder.add_node("qa", self.nodes.qa)
        builder.add_node("repair", self.nodes.repair)
        builder.add_node("deploy", self.nodes.deploy)
        builder.add_node("handover", self.nodes.handover)
        builder.add_node("cancel", self.nodes.cancel)
        builder.add_node("fail", self.nodes.fail)

        # 2. Add START edge
        builder.add_edge(START, "intake")

        # 3. Add conditional routing edges
        builder.add_conditional_edges(
            "intake",
            route_after_intake,
            {"pm_spec": "pm_spec", "cancel": "cancel", "fail": "fail"},
        )

        builder.add_conditional_edges(
            "pm_spec",
            route_after_pm_spec,
            {
                "designer": "designer",
                "await_clarification": "await_clarification",
                "cancel": "cancel",
                "fail": "fail",
            },
        )

        builder.add_conditional_edges(
            "await_clarification",
            route_after_clarification,
            {"pm_spec": "pm_spec", "cancel": "cancel", "fail": "fail"},
        )

        builder.add_conditional_edges(
            "designer",
            route_after_designer,
            {"preview": "preview", "cancel": "cancel", "fail": "fail"},
        )

        builder.add_conditional_edges(
            "preview",
            route_after_preview,
            {"await_approval": "await_approval", "cancel": "cancel", "fail": "fail"},
        )

        builder.add_conditional_edges(
            "await_approval",
            route_after_approval,
            {
                "build": "build",
                "designer": "designer",
                "fail": "fail",
                "cancel": "cancel",
            },
        )

        builder.add_conditional_edges(
            "build",
            route_after_build,
            {"qa": "qa", "fail": "fail", "cancel": "cancel"},
        )

        builder.add_conditional_edges(
            "qa",
            route_after_qa,
            {
                "deploy": "deploy",
                "repair": "repair",
                "fail": "fail",
                "cancel": "cancel",
            },
        )

        builder.add_conditional_edges(
            "repair",
            route_after_repair,
            {"build": "build", "fail": "fail", "cancel": "cancel"},
        )

        builder.add_conditional_edges(
            "deploy",
            route_after_deploy,
            {"handover": "handover", "fail": "fail"},
        )

        # 4. Terminal nodes connect to END
        builder.add_edge("handover", END)
        builder.add_edge("cancel", END)
        builder.add_edge("fail", END)

        # 5. Compile with optional durable checkpointer
        return builder.compile(checkpointer=self.checkpointer)
