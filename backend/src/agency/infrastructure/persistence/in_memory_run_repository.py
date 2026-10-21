"""In-memory implementation of RunRepositoryPort for development and runtime."""

from agency.application.errors import RepositoryError
from agency.application.ports.run_repository import RunRepositoryPort
from agency.domain.entities.run import Run
from agency.domain.enums import RunState


class InMemoryRunRepository(RunRepositoryPort):
    """Thread-safe in-memory repository store for Run aggregates."""

    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}

    def save(self, run: Run) -> None:
        """Save a deep copy of the Run aggregate to prevent mutation."""
        self._runs[run.run_id] = run.model_copy(deep=True)

    def get_by_id(self, run_id: str) -> Run | None:
        """Retrieve a deep copy of the Run aggregate by ID."""
        run = self._runs.get(run_id)
        return run.model_copy(deep=True) if run else None

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        state: RunState | None = None,
    ) -> list[Run]:
        """Return a deterministic, paginated slice of stored runs."""
        if limit < 1 or limit > 100:
            raise RepositoryError(
                f"Invalid limit '{limit}'. Limit must be between 1 and 100."
            )
        if offset < 0:
            raise RepositoryError(f"Invalid offset '{offset}'. Offset must be >= 0.")

        runs = list(self._runs.values())
        if state is not None:
            runs = [r for r in runs if r.state == state]

        # Deterministic sorting by creation timestamp, then run_id
        runs.sort(key=lambda r: (r.created_at, r.run_id))

        slice_result = runs[offset : offset + limit]
        return [r.model_copy(deep=True) for r in slice_result]

    def count(self, state: RunState | None = None) -> int:
        """Return the count of stored runs."""
        if state is None:
            return len(self._runs)
        return sum(1 for r in self._runs.values() if r.state == state)

    def clear(self) -> None:
        """Clear all stored runs."""
        self._runs.clear()
