"""Unit tests for GraphNodes execution in isolation using test doubles."""

from tests.fakes.fake_deploy import FakeDeploy
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_llm import FakeLLM
from tests.fakes.fake_qa_service import FakeQAService
from tests.fakes.fake_run_repository import FakeRunRepository
from tests.fakes.fake_sandbox import FakeSandbox

from agency.application.agents.builder_agent import BuilderAgent
from agency.application.agents.designer_agent import DesignerAgent
from agency.application.agents.models import (
    DesignerOutputSchema,
    PMOutputSchema,
)
from agency.application.agents.pm_agent import PMAgent
from agency.application.graph.nodes import GraphNodes
from agency.application.graph.state import init_workflow_state
from agency.domain.entities.brief import Brief
from agency.domain.entities.page_content import PageContent, SectionContent
from agency.domain.entities.spec import AcceptanceCriterion, Spec, SpecPage, SpecSection
from agency.domain.enums import RunState


def _make_sample_spec() -> Spec:
    return Spec(
        project_id="kaelen-thorne",
        title="Kaelen Thorne — Systems",
        pages=[
            SpecPage(
                slug="home",
                title="Home",
                sections=[
                    SpecSection(
                        id="hero",
                        title="Hero Section",
                        description="State core expertise and background.",
                        required_content=["headline", "bio"],
                    )
                ],
            )
        ],
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                description="Must pass all accessibility standards.",
            )
        ],
    )


def _setup_nodes(
    fake_llm: FakeLLM,
) -> tuple[GraphNodes, FakeRunRepository, FakeEventBus, FakeSandbox, FakeDeploy]:
    repo = FakeRunRepository()
    event_bus = FakeEventBus()
    sandbox = FakeSandbox()
    deploy = FakeDeploy()
    qa_service = FakeQAService()

    pm_agent = PMAgent(llm=fake_llm)
    designer_agent = DesignerAgent(llm=fake_llm)
    builder_agent = BuilderAgent(llm=fake_llm)

    nodes = GraphNodes(
        repository=repo,
        event_bus=event_bus,
        pm_agent=pm_agent,
        designer_agent=designer_agent,
        builder_agent=builder_agent,
        qa_service=qa_service,
        sandbox=sandbox,
        deploy_port=deploy,
    )
    return nodes, repo, event_bus, sandbox, deploy


def test_intake_creates_run_and_emits_run_started() -> None:
    """Intake node instantiates Run aggregate and publishes RunStarted event."""
    fake_llm = FakeLLM()
    nodes, repo, event_bus, _, _ = _setup_nodes(fake_llm)

    brief = Brief(
        client_name="Kaelen Thorne",
        site_type="Systems Portfolio",
        pages=["Home", "About", "Projects", "Contact"],
        tone="Technical",
        content_notes="Distributed systems specialist with 10 years experience.",
    )
    state = init_workflow_state(brief=brief, run_id="run-1", project_id="kaelen")

    result = nodes.intake(state)

    assert result["current_stage"] == "intake"
    saved_run = repo.get_by_id("run-1")
    assert saved_run is not None
    assert saved_run.state == RunState.PLANNING
    assert len(event_bus.events) == 1
    assert event_bus.events[0].__class__.__name__ == "RunStarted"


def test_pm_spec_generates_spec_and_updates_run() -> None:
    """pm_spec produces valid spec from LLM and advances run to PROTOTYPING."""
    fake_llm = FakeLLM()
    sample_spec = _make_sample_spec()
    fake_llm.set_response(
        PMOutputSchema,
        PMOutputSchema(spec=sample_spec, assumptions=["Assumes static Astro"]),
    )
    nodes, repo, event_bus, _, _ = _setup_nodes(fake_llm)

    brief = Brief(
        client_name="Kaelen Thorne",
        site_type="Systems Portfolio",
        pages=["Home"],
        tone="Technical",
        content_notes="Specializing in distributed systems and cloud architecture.",
    )
    state = init_workflow_state(brief=brief, run_id="run-2", project_id="kaelen")
    nodes.intake(state)

    result = nodes.pm_spec(state)

    assert result["current_stage"] == "pm_spec"
    assert result["spec"]["title"] == "Kaelen Thorne — Systems"
    saved_run = repo.get_by_id("run-2")
    assert saved_run is not None
    assert saved_run.state == RunState.PROTOTYPING


def test_designer_generates_tokens_and_content() -> None:
    """designer node produces DesignTokens and PageContent."""
    fake_llm = FakeLLM()
    sample_spec = _make_sample_spec()
    fake_llm.set_response(
        DesignerOutputSchema,
        DesignerOutputSchema(
            theme="editorial",
            font_family="Poppins",
            colors={
                "brand_primary": "#0952C6",
                "bg_base": "#FFFFFF",
                "text_primary": "#1C1B19",
            },
            spacing_scale={"space-1": 4.0},
            border_radius_scale={"radius-sm": 2.0},
            pages=[
                PageContent(
                    page_slug="home",
                    sections=[
                        SectionContent(
                            section_id="hero",
                            section_type="hero",
                            headline="Distributed Systems",
                            copy="Engineering high-availability consensus engines.",
                        )
                    ],
                )
            ],
        ),
    )
    nodes, _, _, _, _ = _setup_nodes(fake_llm)

    state = init_workflow_state(
        brief=Brief(
            client_name="Kaelen",
            site_type="Portfolio",
            pages=["Home"],
            tone="Technical",
            content_notes="Distributed systems specialist.",
        ),
        run_id="run-3",
    )
    state["spec"] = sample_spec.model_dump(mode="json")

    result = nodes.designer(state)

    assert result["current_stage"] == "designer"
    assert result["design_tokens"]["font_family"] == "Poppins"
    assert len(result["page_content"]) == 1


def test_preview_submits_prototype_to_run() -> None:
    """preview node generates preview_ref and transitions Run to AWAITING_APPROVAL."""
    fake_llm = FakeLLM()
    nodes, repo, event_bus, _, _ = _setup_nodes(fake_llm)

    brief = Brief(
        client_name="Kaelen",
        site_type="Portfolio",
        pages=["Home"],
        tone="Technical",
        content_notes="Distributed systems specialist.",
    )
    state = init_workflow_state(brief=brief, run_id="run-4", project_id="kaelen")
    nodes.intake(state)
    run = repo.get_by_id("run-4")
    assert run is not None
    run.finish_planning(_make_sample_spec())
    repo.save(run)

    result = nodes.preview(state)

    assert result["current_stage"] == "preview"
    assert "preview-run-4-rev0" in result["preview_result"]["preview_ref"]
    saved_run = repo.get_by_id("run-4")
    assert saved_run is not None
    assert saved_run.state == RunState.AWAITING_APPROVAL
    assert any(e.__class__.__name__ == "PrototypeReady" for e in event_bus.events)


def test_build_compiles_in_sandbox_and_advances_run() -> None:
    """build node applies tokens/content, executes build, and transitions to TESTING."""
    fake_llm = FakeLLM()
    nodes, repo, event_bus, sandbox, _ = _setup_nodes(fake_llm)

    brief = Brief(
        client_name="Kaelen",
        site_type="Portfolio",
        pages=["Home"],
        tone="Technical",
        content_notes="Distributed systems specialist.",
    )
    state = init_workflow_state(brief=brief, run_id="run-5", project_id="kaelen")
    nodes.intake(state)
    run = repo.get_by_id("run-5")
    assert run is not None
    run.finish_planning(_make_sample_spec())
    run.submit_prototype("preview-ref")
    run.approve_prototype(approver="client", prototype_ref="preview-ref")
    repo.save(run)

    state["design_tokens"] = {
        "font_family": "Poppins",
        "colors": {"brand_primary": "#0952C6"},
    }
    state["page_content"] = [
        {"page_slug": "home", "sections": [{"section_id": "hero", "copy": "Test"}]}
    ]

    result = nodes.build(state)

    assert result["current_stage"] == "build"
    assert result["build_result"]["success"] is True
    saved_run = repo.get_by_id("run-5")
    assert saved_run is not None
    assert saved_run.state == RunState.TESTING


def test_deploy_executes_production_deployment() -> None:
    """deploy node promotes build to production and marks Run COMPLETED."""
    fake_llm = FakeLLM()
    nodes, repo, event_bus, _, deploy = _setup_nodes(fake_llm)

    brief = Brief(
        client_name="Kaelen",
        site_type="Portfolio",
        pages=["Home"],
        tone="Technical",
        content_notes="Distributed systems specialist.",
    )
    state = init_workflow_state(brief=brief, run_id="run-6", project_id="kaelen")
    nodes.intake(state)
    run = repo.get_by_id("run-6")
    assert run is not None
    run.finish_planning(_make_sample_spec())
    run.submit_prototype("preview-ref")
    run.approve_prototype(approver="client", prototype_ref="preview-ref")
    run.start_building(commit_sha="HEAD")
    run.finish_building(commit_sha="HEAD", workspace_path="workspaces/kaelen")
    run.pass_qa(total_checks=6)
    repo.save(run)

    result = nodes.deploy(state)

    assert result["current_stage"] == "deploy"
    preview_url = result["deployment_result"]["preview_url"]
    assert "https://kaelen-preview.agency.run" in preview_url
    saved_run = repo.get_by_id("run-6")
    assert saved_run is not None
    assert saved_run.state == RunState.COMPLETED
    assert any(e.__class__.__name__ == "DeploymentCompleted" for e in event_bus.events)


def test_handover_destroys_sandbox() -> None:
    """handover generates report and cleans up sandbox resources."""
    fake_llm = FakeLLM()
    nodes, _, _, sandbox, _ = _setup_nodes(fake_llm)
    sbx_id = sandbox.create()

    brief = Brief(
        client_name="Kaelen",
        site_type="Portfolio",
        pages=["Home"],
        tone="Technical",
        content_notes="Distributed systems specialist.",
    )
    state = init_workflow_state(brief=brief, run_id="run-7", project_id="kaelen")
    state["sandbox_id"] = sbx_id
    state["deployment_result"] = {
        "preview_url": "https://preview.agency.run",
        "production_url": "https://kaelen.agency.run",
    }

    result = nodes.handover(state)

    assert result["current_stage"] == "handover"
    assert result["handover_report"]["production_url"] == "https://kaelen.agency.run"
    assert sbx_id not in sandbox._sandboxes
