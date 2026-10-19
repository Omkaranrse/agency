"""Unit tests for PageContent and SectionContent entities."""

import pytest
from pydantic import ValidationError

from agency.domain.entities.page_content import PageContent, SectionContent


def mutate_attr(obj: object, name: str, value: object) -> None:
    """Helper to attempt dynamic mutation on frozen objects."""
    setattr(obj, name, value)


def test_valid_page_content_creation() -> None:
    """Test valid PageContent and SectionContent creation."""
    s1 = SectionContent(
        section_id="hero",
        section_type="hero-banner",
        headline="Welcome to Agency",
        copy="Transforming client briefs into production code.",
    )
    s2 = SectionContent(
        section_id="features",
        section_type="feature-grid",
        copy="Clean Architecture, Pydantic v2, and LangGraph.",
    )
    page = PageContent(
        page_slug="home",
        sections=[s1, s2],
    )
    assert page.page_slug == "home"
    assert len(page.sections) == 2
    assert page.sections[0].section_id == "hero"
    assert page.sections[1].section_id == "features"
    assert "Transforming client briefs" in page.sections[0].copy_text


def test_page_content_preserves_section_order() -> None:
    """Test that sections maintain strict order."""
    s1 = SectionContent(section_id="a", section_type="t", copy="Copy A")
    s2 = SectionContent(section_id="b", section_type="t", copy="Copy B")
    s3 = SectionContent(section_id="c", section_type="t", copy="Copy C")

    page = PageContent(page_slug="home", sections=[s2, s3, s1])
    assert [s.section_id for s in page.sections] == ["b", "c", "a"]


def test_page_content_rejects_duplicate_section_ids() -> None:
    """Test that duplicate section IDs within a page are rejected."""
    s1 = SectionContent(section_id="hero", section_type="hero", copy="Copy 1")
    s2 = SectionContent(section_id="Hero", section_type="hero", copy="Copy 2")

    with pytest.raises(ValidationError) as exc_info:
        PageContent(page_slug="home", sections=[s1, s2])
    assert "Duplicate section identifier" in str(exc_info.value)


@pytest.mark.parametrize(
    "invalid_slug",
    ["", "  ", "Home", "home with spaces", "home_underscore"],
)
def test_page_content_rejects_invalid_slugs(invalid_slug: str) -> None:
    """Test that invalid slugs are rejected."""
    s1 = SectionContent(section_id="s1", section_type="type", copy="Copy")
    with pytest.raises(ValidationError):
        PageContent(page_slug=invalid_slug, sections=[s1])


def test_page_content_is_immutable() -> None:
    """Test that PageContent and SectionContent cannot be mutated."""
    s1 = SectionContent(section_id="s1", section_type="type", copy="Copy")
    page = PageContent(page_slug="home", sections=[s1])

    with pytest.raises(ValidationError):
        mutate_attr(page, "page_slug", "about")

    with pytest.raises(ValidationError):
        mutate_attr(s1, "copy_text", "New copy")
