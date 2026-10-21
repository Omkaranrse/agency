"""API route handlers for managing Run aggregate lifecycles."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import HttpUrl

from agency.application.ports.run_repository import RunRepositoryPort
from agency.application.services.workflow_runner import WorkflowRunner
from agency.application.use_cases.get_run import GetRun
from agency.application.use_cases.list_runs import ListRuns, ListRunsQuery
from agency.application.use_cases.start_run import StartRun, StartRunCommand
from agency.domain.entities.brief import Brief
from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.interfaces.api.dependencies import (
    get_api_key,
    get_run_repository,
    get_workflow_runner,
    limit_create_runs,
    limit_read_ops,
)
from agency.interfaces.api.schemas.common import PaginationMeta
from agency.interfaces.api.schemas.runs import (
    CreateRunRequest,
    CreateRunResponse,
    ListRunsResponse,
    RunResponse,
)

router = APIRouter(prefix="/runs", tags=["Runs"])


def _map_run_to_response(run: Run) -> RunResponse:
    """Map a domain Run aggregate to the external RunResponse DTO."""
    approval_state: str | None = None
    if run.approval_recorded:
        approval_state = "approved"
    elif run.state == RunState.AWAITING_APPROVAL:
        approval_state = "pending"

    failure_details = None
    if run.failure_reason:
        failure_details = {"reason": run.failure_reason}
    elif run.cancellation_reason:
        failure_details = {"reason": run.cancellation_reason}

    return RunResponse(
        run_id=run.run_id,
        project_id=run.project_id,
        status=run.state.value,
        current_stage=run.state.value.lower(),
        created_at=run.created_at,
        updated_at=run.updated_at,
        approval_state=approval_state,
        current_revision=run.revision_count,
        preview_url=run.prototype_ref,
        production_url=None,
        build_summary=None,
        qa_summary=None,
        failure_details=failure_details,
    )


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CreateRunResponse,
    dependencies=[Depends(get_api_key), Depends(limit_create_runs)],
)
async def create_run(
    request: CreateRunRequest,
    repository: Annotated[RunRepositoryPort, Depends(get_run_repository)],
    runner: Annotated[WorkflowRunner, Depends(get_workflow_runner)],
) -> CreateRunResponse:
    """Validate client brief, persist initial Run aggregate, and enqueue execution."""
    domain_brief = Brief(
        client_name=request.brief.client_name,
        site_type=request.brief.site_type,
        pages=request.brief.pages,
        tone=request.brief.tone,
        content_notes=request.brief.content_notes,
        links=[HttpUrl(u) for u in request.brief.links],
    )

    raw_pid = request.project_id or request.brief.client_name.lower()
    project_id = raw_pid.replace(" ", "-")

    # Delegate Run creation and initial persistence to StartRun use case
    event_bus = runner.workflow_service.nodes.event_bus
    use_case = StartRun(repository=repository, event_bus=event_bus)
    result = use_case.execute(
        StartRunCommand(
            project_id=project_id,
            brief=domain_brief,
        )
    )

    # Enqueue asynchronous orchestration via supervised WorkflowRunner
    runner.submit_run(
        run_id=result.run_id,
        brief=domain_brief,
        project_id=result.project_id,
        idempotency_key=request.idempotency_key,
    )

    return CreateRunResponse(
        run_id=result.run_id,
        project_id=result.project_id,
        status=result.state.value,
        current_stage="created",
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=ListRunsResponse,
    dependencies=[Depends(get_api_key), Depends(limit_read_ops)],
)
async def list_runs(
    repository: Annotated[RunRepositoryPort, Depends(get_run_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    run_status: Annotated[RunState | None, Query(alias="status")] = None,
) -> ListRunsResponse:
    """Retrieve a paginated, deterministically sorted list of runs."""
    use_case = ListRuns(repository=repository)
    result = use_case.execute(
        ListRunsQuery(limit=limit, offset=offset, state=run_status)
    )

    items = [_map_run_to_response(run) for run in result.items]
    has_next = (result.offset + len(items)) < result.total

    return ListRunsResponse(
        items=items,
        pagination=PaginationMeta(
            total=result.total,
            limit=result.limit,
            offset=result.offset,
            has_next=has_next,
        ),
    )


@router.get(
    "/{run_id}",
    status_code=status.HTTP_200_OK,
    response_model=RunResponse,
    dependencies=[Depends(get_api_key), Depends(limit_read_ops)],
)
async def get_run(
    run_id: str,
    repository: Annotated[RunRepositoryPort, Depends(get_run_repository)],
) -> RunResponse:
    """Retrieve detailed state and metadata for a specific run."""
    use_case = GetRun(repository=repository)
    run = use_case.execute(run_id=run_id)
    return _map_run_to_response(run)
