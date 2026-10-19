"""Client Brief domain entity."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class Brief(BaseModel):
    """Represents a client's original input requirements.

    This model is immutable to preserve the authentic client brief as an
    unaltered input record throughout the multi-agent delivery lifecycle.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    client_name: str = Field(min_length=1, max_length=100)
    site_type: str = Field(min_length=1, max_length=100)
    pages: list[str] = Field(min_length=1, max_length=50)
    tone: str = Field(min_length=1, max_length=100)
    content_notes: str = Field(min_length=1, max_length=10_000)
    links: list[HttpUrl] = Field(default_factory=list, max_length=50)

    @field_validator("client_name", "site_type", "tone", "content_notes", mode="before")
    @classmethod
    def _strip_and_validate_string(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Text fields cannot be empty or whitespace only.")
            return stripped
        return value

    @field_validator("pages", mode="before")
    @classmethod
    def _validate_pages(cls, value: object) -> object:
        if not isinstance(value, list | tuple):
            return value
        if not value:
            raise ValueError("Brief must include at least one page identifier.")

        seen: set[str] = set()
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("Page identifier must be a string.")
            stripped = item.strip()
            if not stripped:
                raise ValueError("Page identifier cannot be empty or whitespace.")
            normalized = stripped.lower()
            if normalized in seen:
                raise ValueError(f"Duplicate page identifier detected: {stripped!r}")
            seen.add(normalized)
            cleaned.append(stripped)
        return cleaned
