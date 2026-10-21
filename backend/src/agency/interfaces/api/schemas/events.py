"""Event schemas for Server-Sent Events (SSE) streaming."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventDTO(BaseModel):
    """Payload representing a single domain event in the event stream."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(description="Unique event cursor identifier")
    run_id: str = Field(description="Associated run aggregate identifier")
    event_type: str = Field(description="Name of the domain event class")
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Sanitized event metadata"
    )
