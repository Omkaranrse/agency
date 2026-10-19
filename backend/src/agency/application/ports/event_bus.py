"""EventBusPort definition for publishing domain events."""

from abc import ABC, abstractmethod

from agency.domain.events import DomainEvent


class EventBusPort(ABC):
    """Abstract port for publishing domain events to downstream listeners.

    Note:
        In-memory implementations are not durable and do not provide
        transactional outbox or distributed transaction guarantees.
    """

    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Publish a single domain event.

        Raises:
            EventPublicationError: If the publishing mechanism fails.
        """

    @abstractmethod
    def publish_all(self, events: list[DomainEvent]) -> None:
        """Publish an ordered sequence of domain events.

        Raises:
            EventPublicationError: If the publishing mechanism fails.
        """
