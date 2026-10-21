"""Common shared response and error schemas for Agency API."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorBody(BaseModel):
    """Detailed error object following the consistent Agency API error format."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(description="Stable machine-readable error code")
    message: str = Field(description="Safe human-readable error description")
    request_id: str = Field(description="Correlation request identifier")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Structured failure diagnostics"
    )


class APIErrorResponse(BaseModel):
    """Top-level error response envelope returned on all 4xx and 5xx errors."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    error: ErrorBody


class PaginationMeta(BaseModel):
    """Pagination metadata for paginated collection responses."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total: int = Field(ge=0, description="Total number of items available")
    limit: int = Field(ge=1, description="Page limit applied to query")
    offset: int = Field(ge=0, description="Offset applied to query")
    has_next: bool = Field(description="True if more pages exist")


class HealthResponse(BaseModel):
    """Health status response schema."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str = Field(default="ok")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    components: dict[str, str] = Field(default_factory=dict)
