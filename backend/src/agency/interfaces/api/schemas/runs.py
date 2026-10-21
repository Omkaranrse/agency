"""Request and response DTO schemas for Run operations."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agency.interfaces.api.schemas.common import PaginationMeta


class BriefDTO(BaseModel):
    """Input client brief data transfer object."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    client_name: str = Field(min_length=1, max_length=100)
    site_type: str = Field(min_length=1, max_length=100)
    pages: list[str] = Field(min_length=1, max_length=20)
    tone: str = Field(min_length=1, max_length=200)
    content_notes: str = Field(min_length=1, max_length=5000)
    links: list[str] = Field(default_factory=list, max_length=50)


class CreateRunRequest(BaseModel):
    """Payload to initiate a new website delivery run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    brief: BriefDTO
    project_id: str | None = Field(default=None, max_length=100)
    template_variant: str | None = Field(default=None, max_length=50)
    idempotency_key: str | None = Field(default=None, max_length=100)


class CreateRunResponse(BaseModel):
    """Response returned when a run creation request is accepted."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    project_id: str
    status: str
    current_stage: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunResponse(BaseModel):
    """Complete summary view of an agency Run aggregate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    project_id: str
    status: str
    current_stage: str
    created_at: datetime
    updated_at: datetime
    approval_state: str | None = None
    current_revision: int = 0
    preview_url: str | None = None
    production_url: str | None = None
    build_summary: dict[str, Any] | None = None
    qa_summary: dict[str, Any] | None = None
    failure_details: dict[str, Any] | None = None


class ListRunsResponse(BaseModel):
    """Paginated collection of Run summaries."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[RunResponse]
    pagination: PaginationMeta
