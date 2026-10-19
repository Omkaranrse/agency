"""In-memory fake implementation of RunRepositoryPort for unit testing."""

from agency.application.errors import RepositoryError
from agency.application.ports.run_repository import RunRepositoryPort
from agency.domain.entities.run import Run
from agency.domain.enums import RunState


class FakeRunRepository(RunRepositoryPort):
    """Deterministic in-memory repository store for Run aggregates."""

    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}
        self._simulated_error: Exception | None = None

    def set_failure(self, error: Exception | None) -> None:
        """Configure a simulated persistence error for testing."""
        self._simulated_error = error

    def clear(self) -> None:
        """Clear all stored runs and reset simulated errors."""
        self._runs.clear()
        self._simulated_error = None

    def save(self, run: Run) -> None:
        """Save a deep copy of the Run aggregate to prevent reference sharing."""
        if self._simulated_error:
            raise self._simulated_error

        # Prevent callers from accidentally mutating stored state through references
        self._runs[run.run_id] = run.model_copy(deep=True)

    def get_by_id(self, run_id: str) -> Run | None:
        """Retrieve a deep copy of the Run aggregate by ID."""
        if self._simulated_error:
            raise self._simulated_error

        run = self._runs.get(run_id)
        return run.model_copy(deep=True) if run else None

    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        state: RunState | None = None,
    ) -> list[Run]:
        """Return a deterministic, paginated slice of stored runs."""
        if self._simulated_error:
            raise self._simulated_error

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
        if self._simulated_error:
            raise self._simulated_error

        if state is None:
            return len(self._runs)
        return sum(1 for r in self._runs.values() if r.state == state)
