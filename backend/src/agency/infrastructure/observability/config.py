"""Configuration models for distributed tracing and observability."""

import os

from pydantic import BaseModel, ConfigDict, Field


class ObservabilityConfig(BaseModel):
    """Runtime configuration for Langfuse tracing and metrics collection."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    enabled: bool = Field(
        default_factory=lambda: (
            os.getenv("LANGFUSE_ENABLED", "false").lower() in ("1", "true", "yes")
        )
    )
    host: str = Field(
        default_factory=lambda: os.getenv(
            "LANGFUSE_HOST", "http://localhost:3000"
        ).rstrip("/")
    )
    public_key: str | None = Field(
        default_factory=lambda: os.getenv("LANGFUSE_PUBLIC_KEY")
    )
    secret_key: str | None = Field(
        default_factory=lambda: os.getenv("LANGFUSE_SECRET_KEY")
    )
    environment: str = Field(
        default_factory=lambda: os.getenv("APP_ENV", "development")
    )
    release: str = Field(default_factory=lambda: os.getenv("APP_RELEASE", "v1.0.0"))
    debug: bool = Field(
        default_factory=lambda: (
            os.getenv("LANGFUSE_DEBUG", "false").lower() in ("1", "true", "yes")
        )
    )
    flush_timeout_seconds: float = Field(default=5.0)

    @property
    def is_configured(self) -> bool:
        """Return True if Langfuse tracing is enabled and credentials are present."""
        return bool(
            self.enabled
            and self.public_key
            and self.secret_key
            and self.public_key.strip()
            and self.secret_key.strip()
        )
