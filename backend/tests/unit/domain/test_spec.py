"""Unit tests for Spec domain entity and nested models."""

import pytest
from pydantic import ValidationError

from agency.domain.entities.spec import (
    AcceptanceCriterion,
    Spec,
    SpecPage,
    SpecSection,
)


def mutate_attr(obj: object, name: str, value: object) -> None:
    """Helper to attempt dynamic mutation on frozen objects."""
    setattr(obj, name, value)


def test_valid_spec_creation() -> None:
    """Test valid Spec, SpecPage, and SpecSection creation."""
    section1 = SpecSection(
        id="hero",
        title="Hero Banner",
        description="Introduces product value proposition.",
        required_content=["Main headline", "CTA button"],
    )
    page1 = SpecPage(
        slug="home",
        title="Homepage",
        sections=[section1],
    )
    criterion1 = AcceptanceCriterion(
        id="AC-1",
        description="Page loads within 1.5 seconds.",
    )
    spec = Spec(
        project_id="proj-101",
        title="Agency MVP Spec",
        pages=[page1],
        technical_constraints=["Node.js 20", "Astro framework"],
        acceptance_criteria=[criterion1],
    )
    assert spec.project_id == "proj-101"
    assert spec.title == "Agency MVP Spec"
    assert len(spec.pages) == 1
    assert spec.pages[0].slug == "home"
    assert len(spec.acceptance_criteria) == 1


def test_spec_page_slug_validation() -> None:
    """Test slug validation rules (lowercase alphanumeric and hyphens)."""
    section = SpecSection(id="s1", title="Title", description="Desc")
    valid_page = SpecPage(slug="about-us", title="About Us", sections=[section])
    assert valid_page.slug == "about-us"

    with pytest.raises(ValidationError):
        SpecPage(slug="about us with spaces", title="Title", sections=[section])

    with pytest.raises(ValidationError):
        SpecPage(slug="AboutUsCamelCase", title="Title", sections=[section])

    with pytest.raises(ValidationError):
        SpecPage(slug="", title="Title", sections=[section])


def test_spec_rejects_duplicate_page_slugs() -> None:
    """Test that Spec rejects duplicate page slugs."""
    section = SpecSection(id="s1", title="Title", description="Desc")
    page1 = SpecPage(slug="home", title="Home 1", sections=[section])
    page2 = SpecPage(slug="home", title="Home 2", sections=[section])
    criterion = AcceptanceCriterion(id="AC-1", description="Criterion")

    with pytest.raises(ValidationError) as exc_info:
        Spec(
            project_id="proj-1",
            title="Spec",
            pages=[page1, page2],
            acceptance_criteria=[criterion],
        )
    assert "Duplicate page slug" in str(exc_info.value)


def test_spec_page_rejects_duplicate_section_ids() -> None:
    """Test that SpecPage rejects duplicate section IDs."""
    s1 = SpecSection(id="hero", title="Hero", description="Hero desc")
    s2 = SpecSection(id="hero", title="Hero 2", description="Duplicate hero")

    with pytest.raises(ValidationError) as exc_info:
        SpecPage(slug="home", title="Home", sections=[s1, s2])
    assert "Duplicate section identifier" in str(exc_info.value)


def test_spec_rejects_duplicate_acceptance_criteria_ids() -> None:
    """Test that Spec rejects duplicate acceptance criteria IDs."""
    section = SpecSection(id="s1", title="Title", description="Desc")
    page = SpecPage(slug="home", title="Home", sections=[section])
    c1 = AcceptanceCriterion(id="AC-1", description="Fast loading")
    c2 = AcceptanceCriterion(id="ac-1", description="SEO friendly")

    with pytest.raises(ValidationError) as exc_info:
        Spec(
            project_id="proj-1",
            title="Spec",
            pages=[page],
            acceptance_criteria=[c1, c2],
        )
    assert "Duplicate acceptance criterion ID" in str(exc_info.value)


def test_spec_rejects_empty_acceptance_criteria() -> None:
    """Test that Spec requires at least one acceptance criterion."""
    section = SpecSection(id="s1", title="Title", description="Desc")
    page = SpecPage(slug="home", title="Home", sections=[section])

    with pytest.raises(ValidationError):
        Spec(
            project_id="proj-1",
            title="Spec",
            pages=[page],
            acceptance_criteria=[],
        )


def test_spec_is_immutable() -> None:
    """Test that Spec and nested entities are immutable."""
    section = SpecSection(id="s1", title="Title", description="Desc")
    page = SpecPage(slug="home", title="Home", sections=[section])
    criterion = AcceptanceCriterion(id="AC-1", description="Criterion")
    spec = Spec(
        project_id="proj-1",
        title="Spec",
        pages=[page],
        acceptance_criteria=[criterion],
    )
    with pytest.raises(ValidationError):
        mutate_attr(spec, "title", "Modified")

    with pytest.raises(ValidationError):
        mutate_attr(section, "title", "Modified")
