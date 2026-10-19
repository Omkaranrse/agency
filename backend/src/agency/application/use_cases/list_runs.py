"""ListRuns use case."""

from pydantic import BaseModel, ConfigDict, Field

from agency.application.ports.run_repository import RunRepositoryPort
from agency.domain.entities.run import Run
from agency.domain.enums import RunState


class ListRunsQuery(BaseModel):
    """Query parameters for paginating and filtering runs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    state: RunState | None = None


class ListRunsResult(BaseModel):
    """Paginated collection of Run aggregates."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[Run]
    total: int
    limit: int
    offset: int


class ListRuns:
    """Use case to query and paginate Run aggregates."""

    def __init__(self, repository: RunRepositoryPort) -> None:
        self._repository = repository

    def execute(self, query: ListRunsQuery | None = None) -> ListRunsResult:
        """Execute the query against the repository port."""
        effective_query = query if query is not None else ListRunsQuery()

        items = self._repository.list(
            limit=effective_query.limit,
            offset=effective_query.offset,
            state=effective_query.state,
        )
        total = self._repository.count(state=effective_query.state)

        return ListRunsResult(
            items=items,
            total=total,
            limit=effective_query.limit,
            offset=effective_query.offset,
        )
