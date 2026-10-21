"""EventFeedPort definition for durable event recording, replay, and live streaming."""

import asyncio
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agency.domain.events import DomainEvent


class EventEnvelope(BaseModel):
    """Structured envelope wrapping domain events for streaming and replay."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)


class EventFeedPort(ABC):
    """Abstract port for persisting, querying, and live streaming domain events."""

    @abstractmethod
    def record_event(self, event: DomainEvent) -> EventEnvelope:
        """Persist a domain event and broadcast to active subscribers."""

    @abstractmethod
    def get_events(
        self,
        run_id: str,
        after_id: str | None = None,
        limit: int = 100,
    ) -> list[EventEnvelope]:
        """Fetch historical events for a run occurring strictly after after_id."""

    @abstractmethod
    def subscribe(self, run_id: str) -> asyncio.Queue[EventEnvelope]:
        """Create a live event subscription queue for a specific run."""

    @abstractmethod
    def unsubscribe(self, run_id: str, queue: asyncio.Queue[EventEnvelope]) -> None:
        """Remove an active subscription queue and release resources."""
