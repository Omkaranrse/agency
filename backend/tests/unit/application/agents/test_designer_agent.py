"""Unit tests for DesignerAgent token and content synthesis."""

import pytest
from tests.fakes.fake_llm import FakeLLM

from agency.application.agents.designer_agent import (
    DesignerAgent,
    DesignerValidationError,
)
from agency.application.agents.models import DesignerOutputSchema, DesignerResult
from agency.application.errors import LLMError
from agency.domain.entities.page_content import PageContent, SectionContent
from agency.domain.entities.spec import AcceptanceCriterion, Spec, SpecPage, SpecSection


def _make_spec() -> Spec:
    return Spec(
        project_id="test-portfolio",
        title="Elena Rostova — Architecture",
        pages=[
            SpecPage(
                slug="home",
                title="Home",
                sections=[
                    SpecSection(
                        id="hero",
                        title="Hero",
                        description="Hero intro",
                    )
                ],
            ),
            SpecPage(
                slug="projects",
                title="Projects",
                sections=[
                    SpecSection(
                        id="grid",
                        title="Projects Grid",
                        description="Project showcase",
                    )
                ],
            ),
        ],
        technical_constraints=["Astro 4", "Tailwind CSS"],
        acceptance_criteria=[
            AcceptanceCriterion(id="ac-1", description="Home renders properly")
        ],
    )


def _make_valid_designer_output() -> DesignerOutputSchema:
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
        spacing_scale={
            "space-1": 4.0,
            "space-2": 8.0,
            "space-4": 16.0,
        },
        border_radius_scale={
            "radius-sm": 2.0,
            "radius-md": 4.0,
        },
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
            ),
            PageContent(
                page_slug="projects",
                sections=[
                    SectionContent(
                        section_id="grid",
                        section_type="projects_grid",
                        headline="Selected Works",
                        copy="Comprehensive residential and civic designs.",
                    )
                ],
            ),
        ],
        assumptions=["Editorial warm palette chosen for architectural client"],
    )


def test_designer_agent_generates_valid_design() -> None:
    """DesignerAgent produces validated DesignTokens and complete PageContent."""
    fake_llm = FakeLLM()
    fake_llm.set_response(DesignerOutputSchema, _make_valid_designer_output())

    agent = DesignerAgent(llm=fake_llm)
    spec = _make_spec()
    result = agent.create_design(spec, run_id="run-des-1")

    assert isinstance(result, DesignerResult)
    assert result.tokens.font_family == "Poppins"
    assert result.tokens.colors["brand_primary"] == "#9C4126"
    assert result.theme == "editorial"
    assert len(result.pages) == 2
    assert result.prompt_version == "v1"

    # Verify FakeLLM call
    assert len(fake_llm.calls) == 1
    call = fake_llm.calls[0]
    assert call["role"] == "designer"
    assert "<untrusted_spec>" in call["prompt"]


def test_designer_agent_rejects_unauthorized_font() -> None:
    """DesignerAgent rejects output using fonts other than Poppins."""
    fake_llm = FakeLLM()
    bad_output = _make_valid_designer_output()
    # Attempt to use Comic Sans
    bad_output.font_family = "Comic Sans MS"
    fake_llm.set_response(DesignerOutputSchema, bad_output)

    agent = DesignerAgent(llm=fake_llm)
    spec = _make_spec()

    with pytest.raises(DesignerValidationError, match="The project requires 'Poppins'"):
        agent.create_design(spec)


def test_designer_agent_rejects_missing_required_color() -> None:
    """DesignerAgent rejects tokens missing mandatory brand or background roles."""
    fake_llm = FakeLLM()
    bad_output = _make_valid_designer_output()
    # Remove brand_primary
    del bad_output.colors["brand_primary"]
    fake_llm.set_response(DesignerOutputSchema, bad_output)

    agent = DesignerAgent(llm=fake_llm)
    spec = _make_spec()

    with pytest.raises(DesignerValidationError, match="missing mandatory color role"):
        agent.create_design(spec)


def test_designer_agent_rejects_lorem_ipsum_placeholders() -> None:
    """DesignerAgent detects and rejects lorem ipsum placeholder copy."""
    fake_llm = FakeLLM()
    bad_output = _make_valid_designer_output()
    bad_output.pages = [
        PageContent(
            page_slug="home",
            sections=[
                SectionContent(
                    section_id="hero",
                    section_type="hero",
                    headline="Architectural Excellence",
                    copy="Lorem ipsum dolor sit amet, consectetur.",
                )
            ],
        ),
        bad_output.pages[1],
    ]
    fake_llm.set_response(DesignerOutputSchema, bad_output)

    agent = DesignerAgent(llm=fake_llm)
    spec = _make_spec()

    with pytest.raises(
        DesignerValidationError, match="Forbidden placeholder or filler text"
    ):
        agent.create_design(spec)


def test_designer_agent_rejects_missing_page_content() -> None:
    """DesignerAgent rejects output missing content for one of the spec pages."""
    fake_llm = FakeLLM()
    bad_output = _make_valid_designer_output()
    # Remove 'projects' page
    bad_output.pages = [p for p in bad_output.pages if p.page_slug != "projects"]
    fake_llm.set_response(DesignerOutputSchema, bad_output)

    agent = DesignerAgent(llm=fake_llm)
    spec = _make_spec()

    with pytest.raises(
        DesignerValidationError, match="Missing content for required spec pages"
    ):
        agent.create_design(spec)


def test_designer_agent_propagates_llm_errors() -> None:
    """DesignerAgent propagates LLM port errors."""
    fake_llm = FakeLLM()
    fake_llm.set_failure(LLMError("Provider timeout"))

    agent = DesignerAgent(llm=fake_llm)
    spec = _make_spec()

    with pytest.raises(LLMError, match="timeout"):
        agent.create_design(spec)
