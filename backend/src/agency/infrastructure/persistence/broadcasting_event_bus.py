"""Broadcasting event bus bridging EventBusPort domain publishing to EventFeedPort."""

from agency.application.ports.event_bus import EventBusPort
from agency.application.ports.event_feed import EventFeedPort
from agency.domain.events import DomainEvent


class BroadcastingEventBus(EventBusPort):
    """Event bus publishing domain events to both an underlying bus and an
    EventFeedPort.
    """

    def __init__(
        self,
        event_feed: EventFeedPort,
        delegate_bus: EventBusPort | None = None,
    ) -> None:
        self.event_feed = event_feed
        self.delegate_bus = delegate_bus

    def publish(self, event: DomainEvent) -> None:
        """Record event into the durable feed and forward to delegate if present."""
        self.event_feed.record_event(event)
        if self.delegate_bus:
            self.delegate_bus.publish(event)

    def publish_all(self, events: list[DomainEvent]) -> None:
        """Record all events into the feed and forward to delegate."""
        for event in events:
            self.event_feed.record_event(event)
        if self.delegate_bus:
            self.delegate_bus.publish_all(events)
