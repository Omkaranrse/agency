"""Page Content domain entity."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SectionContent(BaseModel):
    """Represents the generated content and copy for an individual section."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    section_id: str = Field(min_length=1, max_length=50)
    section_type: str = Field(min_length=1, max_length=50)
    copy_text: str = Field(min_length=1, max_length=50_000, alias="copy")
    headline: str | None = Field(default=None, max_length=200)

    @field_validator("section_id", "section_type", "copy_text", mode="before")
    @classmethod
    def _strip_and_validate_strings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Section field cannot be empty or whitespace only.")
            return stripped
        return value

    @field_validator("headline", mode="before")
    @classmethod
    def _strip_headline(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped if stripped else None
        return value


class PageContent(BaseModel):
    """Represents the ordered content generated for an individual page."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    page_slug: str = Field(min_length=1, max_length=100)
    sections: list[SectionContent] = Field(min_length=1, max_length=50)

    @field_validator("page_slug", mode="before")
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

    @field_validator("sections")
    @classmethod
    def _validate_unique_section_ids(
        cls, sections: list[SectionContent]
    ) -> list[SectionContent]:
        seen_ids: set[str] = set()
        for section in sections:
            normalized = section.section_id.lower()
            if normalized in seen_ids:
                raise ValueError(
                    f"Duplicate section identifier '{section.section_id}' "
                    "detected in page."
                )
            seen_ids.add(normalized)
        return sections
