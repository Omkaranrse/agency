"""Shared fixtures and helper factories for workflow integration tests."""

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from tests.fakes.fake_deploy import FakeDeploy
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_llm import FakeLLM
from tests.fakes.fake_qa_service import FakeQAService
from tests.fakes.fake_run_repository import FakeRunRepository
from tests.fakes.fake_sandbox import FakeSandbox

from agency.application.agents.builder_agent import BuilderAgent
from agency.application.agents.designer_agent import DesignerAgent
from agency.application.agents.models import (
    BuilderOutputSchema,
    BuilderRawEdit,
    DesignerOutputSchema,
    PMOutputSchema,
)
from agency.application.agents.pm_agent import PMAgent
from agency.application.graph.graph_service import WorkflowGraphService
from agency.application.graph.nodes import GraphNodes
from agency.domain.entities.brief import Brief
from agency.domain.entities.page_content import PageContent, SectionContent
from agency.domain.entities.spec import AcceptanceCriterion, Spec, SpecPage, SpecSection


def make_test_brief(
    client_name: str = "Elena Rostova",
    site_type: str = "Architectural Portfolio",
    content_notes: str = (
        "Contemporary sustainable architect specializing in mass timber civic projects."
    ),
    pages: list[str] | None = None,
) -> Brief:
    """Create a validated sample Brief for integration tests."""
    return Brief(
        client_name=client_name,
        site_type=site_type,
        pages=pages or ["Home", "About", "Projects", "Contact"],
        tone="Minimalist, refined, human-centered",
        content_notes=content_notes,
    )


def make_test_spec(project_id: str = "elena-rostova") -> Spec:
    """Create a validated sample Spec for integration tests."""
    return Spec(
        project_id=project_id,
        title="Elena Rostova — Architectural Portfolio",
        pages=[
            SpecPage(
                slug="home",
                title="Home",
                sections=[
                    SpecSection(
                        id="hero",
                        title="Hero Section",
                        description="Core architectural ethos and featured projects.",
                        required_content=["headline", "summary"],
                    )
                ],
            )
        ],
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                description="Must load fast with zero accessibility violations.",
            )
        ],
    )


def make_test_designer_output() -> DesignerOutputSchema:
    """Create a valid DesignerOutputSchema for integration tests."""
    return DesignerOutputSchema(
        theme="editorial",
        font_family="Poppins",
        colors={
            "brand_primary": "#9C4126",
            "brand_hover": "#7D321C",
            "brand_muted": "#EADFD9",
            "bg_base": "#F9F8F6",
            "bg_surface": "#FFFFFF",
            "text_primary": "#1C1B19",
        },
        spacing_scale={"space-1": 4.0, "space-2": 8.0, "space-4": 16.0},
        border_radius_scale={"radius-sm": 2.0, "radius-md": 4.0},
        pages=[
            PageContent(
                page_slug="home",
                sections=[
                    SectionContent(
                        section_id="hero",
                        section_type="hero",
                        headline="Architectural Excellence",
                        copy="Durable, human-centered architectural solutions.",
                    )
                ],
            )
        ],
        assumptions=["Warm editorial palette chosen for architectural client."],
    )


class WorkflowTestHarness:
    """Convenience bundle holding all test fakes and the WorkflowGraphService."""

    def __init__(
        self,
        service: WorkflowGraphService,
        nodes: GraphNodes,
        repository: FakeRunRepository,
        event_bus: FakeEventBus,
        fake_llm: FakeLLM,
        sandbox: FakeSandbox,
        deploy: FakeDeploy,
        qa_service: FakeQAService,
    ) -> None:
        self.service = service
        self.nodes = nodes
        self.repository = repository
        self.event_bus = event_bus
        self.fake_llm = fake_llm
        self.sandbox = sandbox
        self.deploy = deploy
        self.qa_service = qa_service


def build_test_harness(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> WorkflowTestHarness:
    """Construct an isolated test harness with all in-memory fakes."""
    fake_llm = FakeLLM()
    repo = FakeRunRepository()
    event_bus = FakeEventBus()
    sandbox = FakeSandbox()
    deploy = FakeDeploy()
    qa_service = FakeQAService()

    # Pre-configure fake LLM with standard valid outputs
    sample_spec = make_test_spec()
    fake_llm.set_response(PMOutputSchema, PMOutputSchema(spec=sample_spec))
    fake_llm.set_response(DesignerOutputSchema, make_test_designer_output())
    fake_llm.set_response(
        BuilderOutputSchema,
        BuilderOutputSchema(
            edits=[
                BuilderRawEdit(
                    path="src/styles/tokens.css",
                    content="/* safe token repair */",
                    reason="Fix token contrast",
                )
            ]
        ),
    )

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

    service = WorkflowGraphService(nodes=nodes, checkpointer=checkpointer)
    return WorkflowTestHarness(
        service=service,
        nodes=nodes,
        repository=repo,
        event_bus=event_bus,
        fake_llm=fake_llm,
        sandbox=sandbox,
        deploy=deploy,
        qa_service=qa_service,
    )
