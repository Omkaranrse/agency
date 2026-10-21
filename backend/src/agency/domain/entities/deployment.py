"""Deployment domain entity."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class Deployment(BaseModel):
    """Represents deployment metadata for preview or production environments."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    preview_url: HttpUrl
    production_url: HttpUrl | None = None
    provider: str = Field(min_length=1, max_length=100)
    deployed_at: datetime
    deployment_id: str | None = None

    @field_validator("provider", mode="before")
    @classmethod
    def _strip_provider(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError(
                    "Deployment provider cannot be empty or whitespace only."
                )
            return stripped
        return value

    @field_validator("deployed_at")
    @classmethod
    def _validate_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "Deployment deployed_at timestamp must be timezone-aware (UTC)."
            )
        return value

    @property
    def is_production(self) -> bool:
        """Return True if this deployment includes an active production URL."""
        return self.production_url is not None

    @property
    def is_preview(self) -> bool:
        """Return True if this deployment is preview/staging only."""
        return self.production_url is None
