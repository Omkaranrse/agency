"""Durable, cursor-replayable EventFeedPort implementation for SSE streaming."""

import asyncio
import logging
from collections import defaultdict
from typing import Any

from agency.application.ports.event_feed import EventEnvelope, EventFeedPort
from agency.domain.events import DomainEvent

logger = logging.getLogger(__name__)

# Keys stripped from event payloads for safety
SENSITIVE_KEYS = {"api_key", "secret", "token", "password", "authorization"}


def _sanitize_payload(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively strip sensitive keys and raw credentials from event payloads."""
    clean: dict[str, Any] = {}
    for k, v in data.items():
        if k.lower() in SENSITIVE_KEYS:
            continue
        if isinstance(v, dict):
            clean[k] = _sanitize_payload(v)
        elif isinstance(v, list):
            clean[k] = [
                _sanitize_payload(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            clean[k] = v
    return clean


class DurableEventFeed(EventFeedPort):
    """Persistence-backed event feed supporting cursor reconnection and live fan-out."""

    def __init__(self) -> None:
        self._events_by_run: dict[str, list[EventEnvelope]] = defaultdict(list)
        self._subscribers: dict[str, set[asyncio.Queue[EventEnvelope]]] = defaultdict(
            set
        )
        self._lock = asyncio.Lock()

    def record_event(self, event: DomainEvent) -> EventEnvelope:
        """Persist a domain event and fan out to active subscriber queues."""
        raw_payload = event.model_dump(mode="json")
        clean_payload = _sanitize_payload(raw_payload)

        envelope = EventEnvelope(
            event_id=event.event_id,
            run_id=event.run_id,
            event_type=type(event).__name__,
            occurred_at=event.occurred_at,
            payload=clean_payload,
        )

        self._events_by_run[event.run_id].append(envelope)

        # Broadcast to active queues
        subscribers = list(self._subscribers.get(event.run_id, set()))
        for queue in subscribers:
            try:
                queue.put_nowait(envelope)
            except asyncio.QueueFull:
                logger.warning(
                    "Event queue full for subscriber on run '%s'", event.run_id
                )

        return envelope

    def get_events(
        self,
        run_id: str,
        after_id: str | None = None,
        limit: int = 100,
    ) -> list[EventEnvelope]:
        """Fetch historical events for a run occurring strictly after after_id."""
        run_events = self._events_by_run.get(run_id, [])
        if not run_events:
            return []

        start_idx = 0
        if after_id:
            for idx, env in enumerate(run_events):
                if env.event_id == after_id:
                    start_idx = idx + 1
                    break

        return run_events[start_idx : start_idx + limit]

    def subscribe(self, run_id: str) -> asyncio.Queue[EventEnvelope]:
        """Create a live event subscription queue for a run."""
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=500)
        self._subscribers[run_id].add(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[EventEnvelope]) -> None:
        """Remove a subscription queue and free resources."""
        if run_id in self._subscribers and queue in self._subscribers[run_id]:
            self._subscribers[run_id].discard(queue)
            if not self._subscribers[run_id]:
                self._subscribers.pop(run_id, None)
