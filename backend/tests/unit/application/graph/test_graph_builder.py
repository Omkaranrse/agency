"""Unit tests for WorkflowGraphBuilder compilation and structure."""

from tests.fakes.fake_deploy import FakeDeploy
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_llm import FakeLLM
from tests.fakes.fake_qa_service import FakeQAService
from tests.fakes.fake_run_repository import FakeRunRepository
from tests.fakes.fake_sandbox import FakeSandbox

from agency.application.agents.builder_agent import BuilderAgent
from agency.application.agents.designer_agent import DesignerAgent
from agency.application.agents.pm_agent import PMAgent
from agency.application.graph.builder import WorkflowGraphBuilder
from agency.application.graph.nodes import GraphNodes


def test_workflow_graph_builder_compiles_successfully() -> None:
    """WorkflowGraphBuilder compiles StateGraph with all registered nodes."""
    fake_llm = FakeLLM()
    repo = FakeRunRepository()
    event_bus = FakeEventBus()
    sandbox = FakeSandbox()
    deploy = FakeDeploy()
    qa_service = FakeQAService()

    nodes = GraphNodes(
        repository=repo,
        event_bus=event_bus,
        pm_agent=PMAgent(llm=fake_llm),
        designer_agent=DesignerAgent(llm=fake_llm),
        builder_agent=BuilderAgent(llm=fake_llm),
        qa_service=qa_service,
        sandbox=sandbox,
        deploy_port=deploy,
    )

    builder = WorkflowGraphBuilder(nodes=nodes)
    compiled_graph = builder.build()

    assert compiled_graph is not None
    # Verify node presence in compiled graph
    node_keys = compiled_graph.nodes.keys()
    expected_nodes = {
        "intake",
        "pm_spec",
        "await_clarification",
        "designer",
        "preview",
        "await_approval",
        "build",
        "qa",
        "repair",
        "deploy",
        "handover",
        "cancel",
        "fail",
    }
    for expected in expected_nodes:
        assert expected in node_keys
