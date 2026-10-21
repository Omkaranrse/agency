"""In-memory fake implementation of EventFeedPort for testing."""

import asyncio
from collections import defaultdict

from agency.application.ports.event_feed import EventEnvelope, EventFeedPort
from agency.domain.events import DomainEvent


class FakeEventFeed(EventFeedPort):
    """Deterministic in-memory fake event feed."""

    def __init__(self) -> None:
        self._events_by_run: dict[str, list[EventEnvelope]] = defaultdict(list)
        self._subscribers: dict[str, set[asyncio.Queue[EventEnvelope]]] = defaultdict(
            set
        )

    def record_event(self, event: DomainEvent) -> EventEnvelope:
        """Record domain event and fan out to active subscriber queues."""
        envelope = EventEnvelope(
            event_id=event.event_id,
            run_id=event.run_id,
            event_type=type(event).__name__,
            occurred_at=event.occurred_at,
            payload=event.model_dump(mode="json"),
        )
        self._events_by_run[event.run_id].append(envelope)
        for q in list(self._subscribers.get(event.run_id, set())):
            q.put_nowait(envelope)
        return envelope

    def get_events(
        self,
        run_id: str,
        after_id: str | None = None,
        limit: int = 100,
    ) -> list[EventEnvelope]:
        """Fetch historical events for run strictly after after_id."""
        events = self._events_by_run.get(run_id, [])
        if not events:
            return []
        start_idx = 0
        if after_id:
            for idx, e in enumerate(events):
                if e.event_id == after_id:
                    start_idx = idx + 1
                    break
        return events[start_idx : start_idx + limit]

    def subscribe(self, run_id: str) -> asyncio.Queue[EventEnvelope]:
        """Subscribe to a run's live events."""
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue()
        self._subscribers[run_id].add(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[EventEnvelope]) -> None:
        """Unsubscribe queue."""
        if run_id in self._subscribers and queue in self._subscribers[run_id]:
            self._subscribers[run_id].discard(queue)
            if not self._subscribers[run_id]:
                self._subscribers.pop(run_id, None)
