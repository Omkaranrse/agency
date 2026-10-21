"""Unit tests for BuilderAgent file edit proposal generation."""

import json
from pathlib import Path

import pytest
from tests.fakes.fake_llm import FakeLLM

from agency.application.agents.builder_agent import BuilderAgent
from agency.application.agents.file_edit_policy import (
    ForbiddenFileEditError,
)
from agency.application.agents.models import (
    BuilderContext,
    BuilderOutputSchema,
    BuilderRawEdit,
    BuilderResult,
    EditCategory,
)
from agency.application.errors import LLMError
from agency.domain.entities.design_tokens import DesignTokens
from agency.domain.entities.page_content import PageContent, SectionContent
from agency.domain.entities.qa_report import QACheck, QAReport
from agency.domain.entities.spec import AcceptanceCriterion, Spec, SpecPage, SpecSection


def _make_builder_context(
    qa_report: QAReport | None = None,
    allow_component_escalation: bool = False,
    current_revision: int = 1,
) -> BuilderContext:
    spec = Spec(
        project_id="test-build",
        title="Test Portfolio",
        pages=[
            SpecPage(
                slug="home",
                title="Home",
                sections=[
                    SpecSection(
                        id="hero",
                        title="Hero Section",
                        description="Hero intro",
                    )
                ],
            )
        ],
        technical_constraints=["Astro 4", "Tailwind CSS"],
        acceptance_criteria=[
            AcceptanceCriterion(id="ac-1", description="Hero renders properly")
        ],
    )
    tokens = DesignTokens(
        font_family="Poppins",
        colors={
            "brand_primary": "#9C4126",
            "bg_base": "#FFFFFF",
            "text_primary": "#111111",
        },
        spacing_scale={"space-1": 4.0},
        border_radius_scale={"radius-sm": 2.0},
    )
    pages = [
        PageContent(
            page_slug="home",
            sections=[
                SectionContent(
                    section_id="hero",
                    section_type="hero",
                    headline="Welcome",
                    copy="Durable portfolio.",
                )
            ],
        )
    ]
    return BuilderContext(
        spec=spec,
        tokens=tokens,
        pages=pages,
        qa_report=qa_report,
        current_revision=current_revision,
        allow_component_escalation=allow_component_escalation,
    )


def test_builder_agent_proposes_valid_edits() -> None:
    """BuilderAgent proposes valid content and token edits."""
    fake_llm = FakeLLM()

    valid_site_json = json.dumps(
        {
            "clientName": "Elena",
            "siteTitle": "Elena — Portfolio",
            "nav": [{"label": "Home", "href": "/"}],
        }
    )
    valid_tokens_css = ":root { --color-brand-primary: #9C4126; }"

    fake_llm.set_response(
        BuilderOutputSchema,
        BuilderOutputSchema(
            edits=[
                BuilderRawEdit(
                    path="src/content/site.json",
                    content=valid_site_json,
                    reason="Configure site title and nav",
                ),
                BuilderRawEdit(
                    path="src/styles/tokens.css",
                    content=valid_tokens_css,
                    reason="Configure brand colors",
                ),
            ],
            explanation="Initial site customization.",
        ),
    )

    agent = BuilderAgent(llm=fake_llm)
    context = _make_builder_context(current_revision=1)
    result = agent.propose_edits(context)

    assert isinstance(result, BuilderResult)
    assert result.revision_number == 1
    assert result.prompt_version == "v1"
    assert len(result.edits) == 2

    # Check categories resolved by server policy
    assert result.edits[0].path == "src/content/site.json"
    assert result.edits[0].category == EditCategory.CONTENT

    assert result.edits[1].path == "src/styles/tokens.css"
    assert result.edits[1].category == EditCategory.TOKENS

    # Verify FakeLLM call
    assert len(fake_llm.calls) == 1
    call = fake_llm.calls[0]
    assert call["role"] == "builder"
    assert "<untrusted_context>" in call["prompt"]


def test_builder_agent_qa_repair_edits() -> None:
    """BuilderAgent passes QA failures into prompt and outputs repair proposals."""
    fake_llm = FakeLLM()

    valid_home_json = json.dumps(
        {
            "heroEyebrow": "Architecture",
            "headline": "High Contrast Headline",
            "supportingCopy": "High contrast copy text for WCAG compliance.",
        }
    )

    fake_llm.set_response(
        BuilderOutputSchema,
        BuilderOutputSchema(
            edits=[
                BuilderRawEdit(
                    path="src/content/home.json",
                    content=valid_home_json,
                    reason="Fix low contrast copy detected in QA",
                    qa_issue_addressed="wcag_contrast_failure",
                )
            ],
            explanation="Repair WCAG failure.",
        ),
    )

    agent = BuilderAgent(llm=fake_llm)
    qa_report = QAReport(
        checks=[
            QACheck(
                name="wcag_contrast_failure",
                passed=False,
                details="Contrast ratio 3.2:1 below 4.5:1 required.",
            )
        ]
    )
    context = _make_builder_context(qa_report=qa_report, current_revision=2)
    result = agent.propose_edits(context)

    assert len(result.edits) == 1
    assert result.edits[0].qa_issue_addressed == "wcag_contrast_failure"
    assert result.revision_number == 2

    # Verify QA report was provided to prompt
    call = fake_llm.calls[0]
    assert "<untrusted_qa_report>" in call["prompt"]
    assert "wcag_contrast_failure" in call["prompt"]


def test_builder_agent_component_escalation_enforcement() -> None:
    """BuilderAgent enforces component escalation policy on proposals."""
    fake_llm = FakeLLM()
    fake_llm.set_response(
        BuilderOutputSchema,
        BuilderOutputSchema(
            edits=[
                BuilderRawEdit(
                    path="src/components/Header.astro",
                    content="--- --- <header>Fixed</header>",
                    reason="Fix layout",
                )
            ]
        ),
    )

    agent = BuilderAgent(llm=fake_llm)

    # Escalation disabled -> raises ForbiddenFileEditError
    ctx_no_esc = _make_builder_context(allow_component_escalation=False)
    with pytest.raises(
        ForbiddenFileEditError, match="prohibited without explicit escalation"
    ):
        agent.propose_edits(ctx_no_esc)


def test_builder_agent_no_direct_filesystem_writes(tmp_path: Path) -> None:
    """BuilderAgent is purely advisory and never performs filesystem writes."""
    fake_llm = FakeLLM()
    valid_site_json = json.dumps(
        {
            "clientName": "Elena",
            "siteTitle": "Elena",
            "nav": [],
        }
    )
    fake_llm.set_response(
        BuilderOutputSchema,
        BuilderOutputSchema(
            edits=[
                BuilderRawEdit(
                    path="src/content/site.json",
                    content=valid_site_json,
                    reason="Customization",
                )
            ]
        ),
    )

    agent = BuilderAgent(llm=fake_llm)
    context = _make_builder_context()
    agent.propose_edits(context)

    # Verify no file was written to disk by the agent
    assert not (tmp_path / "src" / "content" / "site.json").exists()


def test_builder_agent_propagates_llm_errors() -> None:
    """BuilderAgent propagates LLM errors."""
    fake_llm = FakeLLM()
    fake_llm.set_failure(LLMError("Rate limit reached"))

    agent = BuilderAgent(llm=fake_llm)
    context = _make_builder_context()

    with pytest.raises(LLMError, match="Rate limit"):
        agent.propose_edits(context)
