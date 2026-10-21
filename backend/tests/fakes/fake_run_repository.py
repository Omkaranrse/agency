"""In-memory fake implementation of RunRepositoryPort for unit testing."""

from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.infrastructure.persistence.in_memory_run_repository import (
    InMemoryRunRepository,
)


class FakeRunRepository(InMemoryRunRepository):
    """Deterministic in-memory repository store with simulated errors."""

    def __init__(self) -> None:
        super().__init__()
        self._simulated_error: Exception | None = None

    def set_failure(self, error: Exception | None) -> None:
        """Configure a simulated persistence error for testing."""
        self._simulated_error = error

    def clear(self) -> None:
        """Clear all stored runs and reset simulated errors."""
        super().clear()
        self._simulated_error = None

    def save(self, run: Run) -> None:
        """Save a deep copy of the Run aggregate to prevent reference sharing."""
        if self._simulated_error:
            raise self._simulated_error
        super().save(run)

    def get_by_id(self, run_id: str) -> Run | None:
        """Retrieve a deep copy of the Run aggregate by ID."""
        if self._simulated_error:
            raise self._simulated_error
        return super().get_by_id(run_id)

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        state: RunState | None = None,
    ) -> list[Run]:
        """Return a deterministic, paginated slice of stored runs."""
        if self._simulated_error:
            raise self._simulated_error
        return super().list(limit=limit, offset=offset, state=state)

    def count(self, state: RunState | None = None) -> int:
        """Return the count of stored runs."""
        if self._simulated_error:
            raise self._simulated_error
        return super().count(state=state)
