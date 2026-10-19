"""In-memory fake implementation of EventBusPort for unit testing."""

from agency.application.ports.event_bus import EventBusPort
from agency.domain.events import DomainEvent


class FakeEventBus(EventBusPort):
    """Deterministic in-memory event bus capturing published domain events."""

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []
        self._simulated_error: Exception | None = None

    def set_failure(self, error: Exception | None) -> None:
        """Configure a simulated publication error for testing."""
        self._simulated_error = error

    def clear(self) -> None:
        """Clear all published events and reset simulated errors."""
        self._events.clear()
        self._simulated_error = None

    @property
    def events(self) -> list[DomainEvent]:
        """Return a copy of all published domain events in arrival order."""
        return list(self._events)

    def publish(self, event: DomainEvent) -> None:
        """Capture a published domain event."""
        if self._simulated_error:
            raise self._simulated_error
        self._events.append(event)

    def publish_all(self, events: list[DomainEvent]) -> None:
        """Capture an ordered sequence of published domain events."""
        if self._simulated_error:
            raise self._simulated_error
        self._events.extend(events)
