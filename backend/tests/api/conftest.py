"""Test fixtures and dependency injection overrides for API test suites."""

from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

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
from agency.application.services.workflow_runner import WorkflowRunner
from agency.domain.entities.brief import Brief
from agency.domain.entities.page_content import PageContent, SectionContent
from agency.domain.entities.spec import AcceptanceCriterion, Spec, SpecPage, SpecSection
from agency.infrastructure.persistence import (
    BroadcastingEventBus,
    create_in_memory_checkpointer,
)
from agency.interfaces.api.app import create_app
from agency.interfaces.api.config import APISettings
from agency.interfaces.api.dependencies import (
    get_artifact_storage,
    get_event_bus,
    get_event_feed,
    get_rate_limiter,
    get_run_repository,
    get_settings,
    get_workflow_runner,
    set_artifact_storage,
    set_event_bus,
    set_event_feed,
    set_run_repository,
    set_settings,
    set_workflow_runner,
)
from tests.fakes.fake_artifact_storage import FakeArtifactStorage
from tests.fakes.fake_deploy import FakeDeploy
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_event_feed import FakeEventFeed
from tests.fakes.fake_llm import FakeLLM
from tests.fakes.fake_qa_service import FakeQAService
from tests.fakes.fake_run_repository import FakeRunRepository
from tests.fakes.fake_sandbox import FakeSandbox

TEST_API_KEY = "test-secret-key-12345"


def make_sample_brief(
    client_name: str = "Elena Rostova",
    site_type: str = "Architectural Portfolio",
) -> Brief:
    """Create a sample valid Brief for API tests."""
    return Brief(
        client_name=client_name,
        site_type=site_type,
        pages=["Home", "About", "Projects", "Contact"],
        tone="Minimalist, refined",
        content_notes="Civic sustainable mass timber architecture.",
    )


def make_sample_spec() -> Spec:
    """Create a sample Spec for test LLM responses."""
    return Spec(
        project_id="elena-rostova",
        title="Elena Rostova — Portfolio",
        pages=[
            SpecPage(
                slug="home",
                title="Home",
                sections=[
                    SpecSection(
                        id="hero",
                        title="Hero Section",
                        description="Core architectural ethos.",
                        required_content=["headline", "summary"],
                    )
                ],
            )
        ],
        acceptance_criteria=[
            AcceptanceCriterion(id="AC-1", description="Fast accessible site.")
        ],
    )


class APITestHarness:
    """Test bundle holding fake dependencies and configured FastAPI application."""

    def __init__(
        self,
        app: FastAPI,
        repository: FakeRunRepository,
        event_feed: FakeEventFeed,
        artifact_storage: FakeArtifactStorage,
        runner: WorkflowRunner,
        settings: APISettings,
    ) -> None:
        self.app = app
        self.repository = repository
        self.event_feed = event_feed
        self.artifact_storage = artifact_storage
        self.runner = runner
        self.settings = settings


@pytest.fixture
def harness() -> Iterator[APITestHarness]:
    """Construct an isolated API test harness with fake dependencies."""
    settings = APISettings(
        env="development",
        api_key=TEST_API_KEY,
        allow_unauthenticated=False,
        dashboard_origins=["http://localhost:3000", "https://dashboard.agency.run"],
        max_request_body_size=1048576,
        rate_limit_reads_per_minute=50,
        rate_limit_writes_per_minute=20,
        rate_limit_creates_per_minute=10,
        rate_limit_window_seconds=60,
        sse_keep_alive_seconds=0.1,  # Short keep-alive for tests
    )
    set_settings(settings)

    # Initialize fakes
    repo = FakeRunRepository()
    feed = FakeEventFeed()
    storage = FakeArtifactStorage()
    fake_bus = FakeEventBus()
    broadcasting_bus = BroadcastingEventBus(event_feed=feed, delegate_bus=fake_bus)

    fake_llm = FakeLLM()
    fake_llm.set_response(PMOutputSchema, PMOutputSchema(spec=make_sample_spec()))
    fake_llm.set_response(
        DesignerOutputSchema,
        DesignerOutputSchema(
            theme="editorial",
            font_family="Poppins",
            colors={"brand_primary": "#9C4126", "bg_base": "#F9F8F6"},
            spacing_scale={"space-1": 4.0},
            border_radius_scale={"radius-sm": 2.0},
            pages=[
                PageContent(
                    page_slug="home",
                    sections=[
                        SectionContent(
                            section_id="hero",
                            section_type="hero",
                            headline="Timber Works",
                            copy="Sustainable mass timber.",
                        )
                    ],
                )
            ],
            assumptions=["Editorial aesthetic."],
        ),
    )
    fake_llm.set_response(
        BuilderOutputSchema,
        BuilderOutputSchema(
            edits=[
                BuilderRawEdit(
                    path="src/styles/tokens.css",
                    content="/* safe edit */",
                    reason="Fix contrast",
                )
            ]
        ),
    )

    nodes = GraphNodes(
        repository=repo,
        event_bus=broadcasting_bus,
        pm_agent=PMAgent(llm=fake_llm),
        designer_agent=DesignerAgent(llm=fake_llm),
        builder_agent=BuilderAgent(llm=fake_llm),
        qa_service=FakeQAService(),
        sandbox=FakeSandbox(),
        deploy_port=FakeDeploy(),
    )

    checkpointer = create_in_memory_checkpointer()
    workflow_service = WorkflowGraphService(nodes=nodes, checkpointer=checkpointer)
    runner = WorkflowRunner(workflow_service=workflow_service, sync_mode=True)

    set_run_repository(repo)
    set_event_feed(feed)
    set_artifact_storage(storage)
    set_workflow_runner(runner)
    set_event_bus(broadcasting_bus)

    # Reset rate limiter
    get_rate_limiter().clear()

    app = create_app(settings)

    # Apply explicit dependency overrides to be completely isolated
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_run_repository] = lambda: repo
    app.dependency_overrides[get_event_feed] = lambda: feed
    app.dependency_overrides[get_artifact_storage] = lambda: storage
    app.dependency_overrides[get_workflow_runner] = lambda: runner
    app.dependency_overrides[get_event_bus] = lambda: broadcasting_bus

    h = APITestHarness(
        app=app,
        repository=repo,
        event_feed=feed,
        artifact_storage=storage,
        runner=runner,
        settings=settings,
    )
    yield h

    app.dependency_overrides.clear()


@pytest.fixture
def client(harness: APITestHarness) -> Iterator[TestClient]:
    """Provide a TestClient pre-configured with the default valid API key header."""
    with TestClient(
        harness.app,
        headers={"X-API-Key": TEST_API_KEY},
        base_url="http://testserver",
    ) as c:
        yield c


@pytest.fixture
async def async_client(harness: APITestHarness) -> AsyncIterator[AsyncClient]:
    """Provide an AsyncClient for SSE and asynchronous testing."""
    async with AsyncClient(
        transport=ASGITransport(app=harness.app),
        base_url="http://testserver",
        headers={"X-API-Key": TEST_API_KEY},
    ) as ac:
        yield ac
