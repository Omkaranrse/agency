"""Technical and functional Specification domain entity."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SpecSection(BaseModel):
    """Represents a discrete section within a page specification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    required_content: list[str] = Field(default_factory=list, max_length=50)
    behavior_notes: str | None = Field(default=None, max_length=1000)

    @field_validator("id", "title", "description", mode="before")
    @classmethod
    def _strip_and_validate_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Section field cannot be empty or whitespace only.")
            return stripped
        return value

    @field_validator("required_content", mode="before")
    @classmethod
    def _validate_content_list(cls, value: object) -> object:
        if not isinstance(value, list | tuple):
            return value
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("Required content item must be a string.")
            stripped = item.strip()
            if not stripped:
                raise ValueError("Required content item cannot be empty.")
            cleaned.append(stripped)
        return cleaned


class SpecPage(BaseModel):
    """Represents a planned page within the project specification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    slug: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=100)
    sections: list[SpecSection] = Field(min_length=1, max_length=50)

    @field_validator("slug", mode="before")
    @classmethod
    def _validate_slug(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Page slug cannot be empty or whitespace.")
            if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", stripped):
                raise ValueError(
                    f"Page slug '{stripped}' must contain only lowercase "
                    "alphanumeric characters and single hyphens."
                )
            return stripped
        return value

    @field_validator("title", mode="before")
    @classmethod
    def _strip_title(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Page title cannot be empty.")
            return stripped
        return value

    @field_validator("sections")
    @classmethod
    def _validate_unique_sections(
        cls, sections: list[SpecSection]
    ) -> list[SpecSection]:
        seen: set[str] = set()
        for section in sections:
            normalized = section.id.lower()
            if normalized in seen:
                raise ValueError(
                    f"Duplicate section identifier '{section.id}' within page."
                )
            seen.add(normalized)
        return sections


class AcceptanceCriterion(BaseModel):
    """An individually identifiable acceptance criterion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=1000)

    @field_validator("id", "description", mode="before")
    @classmethod
    def _strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or whitespace only.")
            return stripped
        return value


class Spec(BaseModel):
    """Represents the approved technical and functional specification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    pages: list[SpecPage] = Field(min_length=1, max_length=50)
    technical_constraints: list[str] = Field(default_factory=list, max_length=50)
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1, max_length=100)

    @field_validator("project_id", "title", mode="before")
    @classmethod
    def _strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Field cannot be empty or whitespace only.")
            return stripped
        return value

    @field_validator("pages")
    @classmethod
    def _validate_unique_page_slugs(cls, pages: list[SpecPage]) -> list[SpecPage]:
        seen_slugs: set[str] = set()
        for page in pages:
            if page.slug in seen_slugs:
                raise ValueError(
                    f"Duplicate page slug '{page.slug}' detected in specification."
                )
            seen_slugs.add(page.slug)
        return pages

    @field_validator("technical_constraints", mode="before")
    @classmethod
    def _validate_constraints(cls, value: object) -> object:
        if not isinstance(value, list | tuple):
            return value
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("Technical constraint must be a string.")
            stripped = item.strip()
            if not stripped:
                raise ValueError("Technical constraint cannot be empty.")
            cleaned.append(stripped)
        return cleaned

    @field_validator("acceptance_criteria")
    @classmethod
    def _validate_criteria_uniqueness(
        cls, criteria: list[AcceptanceCriterion]
    ) -> list[AcceptanceCriterion]:
        seen_ids: set[str] = set()
        for criterion in criteria:
            normalized = criterion.id.lower()
            if normalized in seen_ids:
                raise ValueError(
                    f"Duplicate acceptance criterion ID detected: '{criterion.id}'."
                )
            seen_ids.add(normalized)
        return criteria
