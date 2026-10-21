"""Unit tests for WorkflowGraphService helper methods and initialization."""

from tests.fakes.fake_deploy import FakeDeploy
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_llm import FakeLLM
from tests.fakes.fake_qa_service import FakeQAService
from tests.fakes.fake_run_repository import FakeRunRepository
from tests.fakes.fake_sandbox import FakeSandbox

from agency.application.agents.builder_agent import BuilderAgent
from agency.application.agents.designer_agent import DesignerAgent
from agency.application.agents.pm_agent import PMAgent
from agency.application.graph.graph_service import WorkflowGraphService
from agency.application.graph.nodes import GraphNodes


def test_graph_service_initialization() -> None:
    """WorkflowGraphService properly builds graph and handles clean state extraction."""
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

    service = WorkflowGraphService(nodes=nodes)
    assert service.graph is not None

    # Test clean state extractor
    raw_state = {
        "run_id": "r1",
        "current_stage": "intake",
        "__interrupt__": ["data"],
        "__metadata__": {},
    }
    clean = service._extract_clean_state(raw_state)
    assert "run_id" in clean
    assert "__interrupt__" not in clean
    assert "__metadata__" not in clean
