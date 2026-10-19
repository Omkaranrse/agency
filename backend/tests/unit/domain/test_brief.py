"""Unit tests for Brief domain entity."""

from typing import Any

import pytest
from pydantic import HttpUrl, ValidationError

from agency.domain.entities.brief import Brief


def mutate_attr(obj: object, name: str, value: object) -> None:
    """Helper to attempt dynamic mutation on frozen objects."""
    setattr(obj, name, value)


def test_valid_brief_creation() -> None:
    """Test standard valid Brief creation."""
    brief = Brief(
        client_name="Acme Corp",
        site_type="Marketing Landing Page",
        pages=["home", "about", "contact"],
        tone="Professional and modern",
        content_notes="Focus on B2B SaaS solutions.",
        links=[HttpUrl("https://example.com/brand")],
    )
    assert brief.client_name == "Acme Corp"
    assert brief.site_type == "Marketing Landing Page"
    assert brief.pages == ["home", "about", "contact"]
    assert brief.tone == "Professional and modern"
    assert brief.content_notes == "Focus on B2B SaaS solutions."
    assert len(brief.links) == 1


def test_brief_strips_whitespace() -> None:
    """Test that text fields have unnecessary whitespace stripped."""
    brief = Brief(
        client_name="  Acme Corp  ",
        site_type="\tMarketing Landing Page\n",
        pages=["  home  ", " about "],
        tone="  Friendly  ",
        content_notes="   Some notes   ",
    )
    assert brief.client_name == "Acme Corp"
    assert brief.site_type == "Marketing Landing Page"
    assert brief.pages == ["home", "about"]
    assert brief.tone == "Friendly"
    assert brief.content_notes == "Some notes"


@pytest.mark.parametrize(
    "field,value",
    [
        ("client_name", ""),
        ("client_name", "   "),
        ("site_type", ""),
        ("site_type", " \t "),
        ("tone", ""),
        ("content_notes", ""),
        ("content_notes", "  \n  "),
    ],
)
def test_brief_rejects_empty_or_whitespace_strings(field: str, value: str) -> None:
    """Test that empty or whitespace-only text values raise ValidationError."""
    payload: dict[str, Any] = {
        "client_name": "Acme",
        "site_type": "Portfolio",
        "pages": ["home"],
        "tone": "Warm",
        "content_notes": "Notes",
    }
    payload[field] = value
    with pytest.raises(ValidationError):
        Brief(**payload)


def test_brief_rejects_empty_pages() -> None:
    """Test that an empty pages list is rejected."""
    with pytest.raises(ValidationError):
        Brief(
            client_name="Acme",
            site_type="Portfolio",
            pages=[],
            tone="Warm",
            content_notes="Notes",
        )


def test_brief_rejects_duplicate_pages() -> None:
    """Test that duplicate page identifiers (case-insensitive) are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Brief(
            client_name="Acme",
            site_type="Portfolio",
            pages=["home", "about", "Home"],
            tone="Warm",
            content_notes="Notes",
        )
    assert "Duplicate page identifier" in str(exc_info.value)


def test_brief_rejects_empty_page_identifier() -> None:
    """Test that empty string inside pages list is rejected."""
    with pytest.raises(ValidationError):
        Brief(
            client_name="Acme",
            site_type="Portfolio",
            pages=["home", "   "],
            tone="Warm",
            content_notes="Notes",
        )


def test_brief_validates_urls() -> None:
    """Test that invalid URLs are rejected."""
    raw_links: list[Any] = ["ftp://invalid-protocol.com"]
    with pytest.raises(ValidationError):
        Brief(
            client_name="Acme",
            site_type="Portfolio",
            pages=["home"],
            tone="Warm",
            content_notes="Notes",
            links=raw_links,
        )


def test_brief_is_immutable() -> None:
    """Test that Brief instances cannot be mutated after creation."""
    brief = Brief(
        client_name="Acme",
        site_type="Portfolio",
        pages=["home"],
        tone="Warm",
        content_notes="Notes",
    )
    with pytest.raises(ValidationError):
        mutate_attr(brief, "client_name", "New Name")
