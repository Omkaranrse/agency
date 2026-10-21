"""Deterministic golden output tests for PM, Designer, and Builder agent flows."""

import json

import pytest
from tests.fakes.fake_llm import FakeLLM

from agency.application.agents.builder_agent import BuilderAgent
from agency.application.agents.designer_agent import (
    DesignerAgent,
    DesignerValidationError,
)
from agency.application.agents.file_edit_policy import (
    EditLimitExceededError,
    ForbiddenFileEditError,
    InvalidFileContentError,
)
from agency.application.agents.models import (
    BuilderContext,
    BuilderOutputSchema,
    BuilderRawEdit,
    DesignerOutputSchema,
    EditCategory,
    PMClarificationResult,
    PMOutputSchema,
    PMSpecResult,
)
from agency.application.agents.pm_agent import PMAgent
from agency.domain.entities.brief import Brief
from agency.domain.entities.design_tokens import DesignTokens
from agency.domain.entities.page_content import PageContent, SectionContent
from agency.domain.entities.spec import AcceptanceCriterion, Spec, SpecPage, SpecSection

# ==============================================================================
# Golden Fixtures
# ==============================================================================

GOLDEN_BRIEF = Brief(
    client_name="Kaelen Thorne",
    site_type="Systems Architecture Portfolio",
    pages=["Home", "About", "Projects", "Contact"],
    tone="Authoritative, meticulous, and minimal",
    content_notes=(
        "Staff distributed systems engineer with 12 years building fault-tolerant "
        "consensus engines and real-time streaming pipelines."
    ),
)

GOLDEN_SPEC = Spec(
    project_id="kaelen-thorne-systems",
    title="Kaelen Thorne — Systems Architecture Portfolio",
    pages=[
        SpecPage(
            slug="home",
            title="Home",
            sections=[
                SpecSection(
                    id="hero",
                    title="Hero",
                    description="Systems architecture executive overview",
                ),
                SpecSection(
                    id="featured-work",
                    title="Featured Systems",
                    description="Distributed consensus and stream processing",
                ),
            ],
        ),
        SpecPage(
            slug="about",
            title="About",
            sections=[
                SpecSection(
                    id="bio",
                    title="Biography",
                    description="Career journey and distributed systems philosophy",
                )
            ],
        ),
        SpecPage(
            slug="projects",
            title="Projects",
            sections=[
                SpecSection(
                    id="projects-list",
                    title="Projects Showcase",
                    description="Technical deep dives into open-source engines",
                )
            ],
        ),
        SpecPage(
            slug="contact",
            title="Contact",
            sections=[
                SpecSection(
                    id="contact-info",
                    title="Direct Communication",
                    description="PGP and encrypted contact methods",
                )
            ],
        ),
    ],
    technical_constraints=[
        "Astro 4 SSG",
        "Tailwind CSS",
        "Poppins typography",
        "WCAG 2.2 AA compliant contrast",
    ],
    acceptance_criteria=[
        AcceptanceCriterion(
            id="ac-1", description="Home page renders architectural focus headline"
        ),
        AcceptanceCriterion(
            id="ac-2", description="Projects page showcases fault-tolerant engines"
        ),
    ],
)

GOLDEN_DESIGN_TOKENS = DesignTokens(
    font_family="Poppins",
    colors={
        "brand_primary": "#0952C6",
        "brand_hover": "#063C93",
        "brand_muted": "#E2ECFA",
        "bg_base": "#FFFFFF",
        "bg_surface": "#F5F7FA",
        "text_primary": "#0C1017",
    },
    spacing_scale={
        "space-1": 4.0,
        "space-2": 8.0,
        "space-4": 16.0,
        "space-8": 32.0,
        "space-16": 64.0,
    },
    border_radius_scale={
        "radius-sm": 6.0,
        "radius-md": 10.0,
        "radius-lg": 16.0,
    },
)

GOLDEN_PAGES = [
    PageContent(
        page_slug="home",
        sections=[
            SectionContent(
                section_id="hero",
                section_type="hero",
                headline="Distributed Systems Architecture",
                copy="Engineering durable, high-throughput consensus engines.",
            ),
            SectionContent(
                section_id="featured-work",
                section_type="featured_projects",
                headline="Selected Systems",
                copy="High-availability pipelines and Raft consensus engines.",
            ),
        ],
    ),
    PageContent(
        page_slug="about",
        sections=[
            SectionContent(
                section_id="bio",
                section_type="bio",
                headline="Background & Philosophy",
                copy="Over a decade specializing in distributed invariants.",
            )
        ],
    ),
    PageContent(
        page_slug="projects",
        sections=[
            SectionContent(
                section_id="projects-list",
                section_type="projects_grid",
                headline="Open Source Engines",
                copy="Durable distributed message queues and zero-copy RPC layers.",
            )
        ],
    ),
    PageContent(
        page_slug="contact",
        sections=[
            SectionContent(
                section_id="contact-info",
                section_type="contact_form",
                headline="Inquiries & Advisory",
                copy="Available for high-stakes distributed architecture reviews.",
            )
        ],
    ),
]


# ==============================================================================
# Golden Tests
# ==============================================================================


def test_golden_pm_spec_generation() -> None:
    """Golden Brief produces a fully validated Spec matching expected structure."""
    fake_llm = FakeLLM()
    fake_llm.set_response(
        PMOutputSchema,
        PMOutputSchema(
            needs_clarification=False,
            spec=GOLDEN_SPEC,
            assumptions=["Static documentation deployment"],
        ),
    )

    agent = PMAgent(llm=fake_llm)
    result = agent.generate_spec(GOLDEN_BRIEF)

    assert isinstance(result, PMSpecResult)
    assert result.status == "spec"
    assert result.spec.project_id == "kaelen-thorne-systems"
    assert len(result.spec.pages) == 4
    assert result.spec.acceptance_criteria[0].id == "ac-1"


def test_golden_pm_clarification_flow() -> None:
    """Brief requesting dynamic databases triggers deterministic clarification."""
    fake_llm = FakeLLM()
    agent = PMAgent(llm=fake_llm)

    unsupported_brief = Brief(
        client_name="SaaS Startup",
        site_type="E-commerce Store",
        pages=["Home", "Cart", "Checkout"],
        tone="Punchy",
        content_notes="Needs a real-time MongoDB database and Stripe checkout.",
    )

    result = agent.generate_spec(unsupported_brief)
    assert isinstance(result, PMClarificationResult)
    assert result.status == "clarification"
    assert "supported_architecture" in result.missing_fields
    assert len(fake_llm.calls) == 0


def test_golden_designer_synthesis() -> None:
    """DesignerAgent produces validated DesignTokens and all required PageContent."""
    fake_llm = FakeLLM()
    fake_llm.set_response(
        DesignerOutputSchema,
        DesignerOutputSchema(
            theme="studio",
            font_family="Poppins",
            colors=GOLDEN_DESIGN_TOKENS.colors,
            spacing_scale=GOLDEN_DESIGN_TOKENS.spacing_scale,
            border_radius_scale=GOLDEN_DESIGN_TOKENS.border_radius_scale,
            pages=GOLDEN_PAGES,
            assumptions=["Studio theme selected for technical systems persona"],
        ),
    )

    agent = DesignerAgent(llm=fake_llm)
    result = agent.create_design(GOLDEN_SPEC)

    assert result.theme == "studio"
    assert result.tokens.font_family == "Poppins"
    assert len(result.pages) == 4
    slugs = {p.page_slug for p in result.pages}
    assert slugs == {"home", "about", "projects", "contact"}


def test_golden_designer_rejects_lorem_ipsum_fabrication() -> None:
    """DesignerAgent rejects output containing lorem ipsum filler text."""
    fake_llm = FakeLLM()
    fake_llm.set_response(
        DesignerOutputSchema,
        DesignerOutputSchema(
            theme="studio",
            font_family="Poppins",
            colors=GOLDEN_DESIGN_TOKENS.colors,
            spacing_scale=GOLDEN_DESIGN_TOKENS.spacing_scale,
            border_radius_scale=GOLDEN_DESIGN_TOKENS.border_radius_scale,
            pages=[
                PageContent(
                    page_slug="home",
                    sections=[
                        SectionContent(
                            section_id="hero",
                            section_type="hero",
                            headline="Lorem Ipsum Headline",
                            copy="Lorem ipsum dolor sit amet, consectetur elit.",
                        )
                    ],
                ),
                *GOLDEN_PAGES[1:],
            ],
        ),
    )

    agent = DesignerAgent(llm=fake_llm)
    with pytest.raises(DesignerValidationError, match="Forbidden placeholder"):
        agent.create_design(GOLDEN_SPEC)


def test_golden_builder_edit_proposals() -> None:
    """BuilderAgent produces verified proposals for site.json and tokens.css."""
    fake_llm = FakeLLM()
    valid_site_json = json.dumps(
        {
            "clientName": "Kaelen Thorne",
            "siteTitle": "Kaelen Thorne — Systems",
            "nav": [{"label": "Home", "href": "/"}],
        }
    )
    valid_tokens_css = ":root { --color-brand-primary: #0952C6; }"

    fake_llm.set_response(
        BuilderOutputSchema,
        BuilderOutputSchema(
            edits=[
                BuilderRawEdit(
                    path="src/content/site.json",
                    content=valid_site_json,
                    reason="Configure Kaelen Thorne site settings",
                ),
                BuilderRawEdit(
                    path="src/styles/tokens.css",
                    content=valid_tokens_css,
                    reason="Apply Studio brand colors",
                ),
            ],
            explanation="Customize site and tokens.",
        ),
    )

    agent = BuilderAgent(llm=fake_llm)
    context = BuilderContext(
        spec=GOLDEN_SPEC,
        tokens=GOLDEN_DESIGN_TOKENS,
        pages=GOLDEN_PAGES,
        current_revision=1,
    )
    result = agent.propose_edits(context)

    assert result.revision_number == 1
    assert len(result.edits) == 2
    assert result.edits[0].category == EditCategory.CONTENT
    assert result.edits[1].category == EditCategory.TOKENS


def test_golden_builder_rejects_unauthorized_package_json_edit() -> None:
    """BuilderAgent blocks proposals targeting disallowed package.json file."""
    fake_llm = FakeLLM()
    fake_llm.set_response(
        BuilderOutputSchema,
        BuilderOutputSchema(
            edits=[
                BuilderRawEdit(
                    path="package.json",
                    content='{"scripts": {"build": "evil"}}',
                    reason="Inject build script",
                )
            ]
        ),
    )

    agent = BuilderAgent(llm=fake_llm)
    context = BuilderContext(
        spec=GOLDEN_SPEC,
        tokens=GOLDEN_DESIGN_TOKENS,
        pages=GOLDEN_PAGES,
    )

    with pytest.raises(
        ForbiddenFileEditError, match="not in the allowed modification list"
    ):
        agent.propose_edits(context)


def test_golden_builder_rejects_unauthorized_component_edit() -> None:
    """BuilderAgent blocks component edits when escalation is not authorized."""
    fake_llm = FakeLLM()
    fake_llm.set_response(
        BuilderOutputSchema,
        BuilderOutputSchema(
            edits=[
                BuilderRawEdit(
                    path="src/components/Header.astro",
                    content="<header>Unauthorized</header>",
                    reason="Redesign header component",
                )
            ]
        ),
    )

    agent = BuilderAgent(llm=fake_llm)
    context = BuilderContext(
        spec=GOLDEN_SPEC,
        tokens=GOLDEN_DESIGN_TOKENS,
        pages=GOLDEN_PAGES,
        allow_component_escalation=False,
    )

    with pytest.raises(
        ForbiddenFileEditError, match="prohibited without explicit escalation"
    ):
        agent.propose_edits(context)


def test_golden_builder_rejects_invalid_json_proposal() -> None:
    """BuilderAgent blocks proposals containing malformed JSON."""
    fake_llm = FakeLLM()
    fake_llm.set_response(
        BuilderOutputSchema,
        BuilderOutputSchema(
            edits=[
                BuilderRawEdit(
                    path="src/content/site.json",
                    content="{ broken json, missing quote: 123 }",
                    reason="Update site",
                )
            ]
        ),
    )

    agent = BuilderAgent(llm=fake_llm)
    context = BuilderContext(
        spec=GOLDEN_SPEC,
        tokens=GOLDEN_DESIGN_TOKENS,
        pages=GOLDEN_PAGES,
    )

    with pytest.raises(InvalidFileContentError, match="Invalid JSON syntax"):
        agent.propose_edits(context)


def test_golden_builder_rejects_excessive_edits() -> None:
    """BuilderAgent rejects proposals exceeding maximum edit count."""
    fake_llm = FakeLLM()
    raw_edits = [
        BuilderRawEdit(
            path=f"src/content/file_{i}.json", content="{}", reason="Batch edit"
        )
        for i in range(15)
    ]
    fake_llm.set_response(
        BuilderOutputSchema,
        BuilderOutputSchema(edits=raw_edits),
    )

    agent = BuilderAgent(llm=fake_llm)
    context = BuilderContext(
        spec=GOLDEN_SPEC,
        tokens=GOLDEN_DESIGN_TOKENS,
        pages=GOLDEN_PAGES,
    )

    with pytest.raises(EditLimitExceededError, match="exceeding limit"):
        agent.propose_edits(context)
