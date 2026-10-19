"""RunRepositoryPort definition for Run aggregate persistence."""

from abc import ABC, abstractmethod

from agency.domain.entities.run import Run
from agency.domain.enums import RunState


class RunRepositoryPort(ABC):
    """Abstract port for managing persistence of the Run aggregate."""

    @abstractmethod
    def save(self, run: Run) -> None:
        """Persist or update a Run aggregate.

        Raises:
            RepositoryError: If the persistence store fails to save the record.
        """

    @abstractmethod
    def get_by_id(self, run_id: str) -> Run | None:
        """Retrieve a Run aggregate by unique identifier.

        Returns:
            The Run aggregate if found, or None if it does not exist.

        Raises:
            RepositoryError: If the persistence store encounters an error.
        """

    @abstractmethod
    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        state: RunState | None = None,
    ) -> list[Run]:
        """Retrieve a paginated slice of Run aggregates, optionally filtered by state.

        Args:
            limit: Maximum number of runs to return (1-100).
            offset: Zero-indexed position from which to return items.
            state: Optional state filter.

        Returns:
            A list of Run aggregates in deterministic order.
        """

    @abstractmethod
    def count(self, state: RunState | None = None) -> int:
        """Return the total number of runs, optionally filtered by state."""
