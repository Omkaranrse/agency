"""GetRun use case."""

from agency.application.errors import InvalidRequestError, RunNotFoundError
from agency.application.ports.run_repository import RunRepositoryPort
from agency.domain.entities.run import Run


class GetRun:
    """Use case to retrieve a single Run aggregate by ID.

    Guarantees:
    - Queries the RunRepositoryPort.
    - Raises RunNotFoundError if the run does not exist.
    - Returns a deep copy to prevent callers from mutating repository state.
    """

    def __init__(self, repository: RunRepositoryPort) -> None:
        self._repository = repository

    def execute(self, run_id: str) -> Run:
        """Retrieve a run by its unique identifier.

        Raises:
            InvalidRequestError: If run_id is empty or whitespace.
            RunNotFoundError: If no run exists with the specified ID.
        """
        stripped_id = run_id.strip() if isinstance(run_id, str) else ""
        if not stripped_id:
            raise InvalidRequestError("Run ID cannot be empty or whitespace.")

        run = self._repository.get_by_id(stripped_id)
        if run is None:
            raise RunNotFoundError(stripped_id)

        # Return deep copy to prevent mutating stored aggregate state
        return run.model_copy(deep=True)
