"""API route handlers for virtual office state and employee tasks."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from agency.application.office.models import OfficeState, TaskRecord
from agency.application.office.service import OfficeStateService
from agency.interfaces.api.dependencies import (
    get_api_key,
    get_office_state_service,
    limit_read_ops,
)
from agency.interfaces.api.schemas.office import (
    ListTasksResponse,
    OfficeEmployeeDTO,
    OfficeStateResponse,
    TaskRecordDTO,
    WorkstationDTO,
)

router = APIRouter(prefix="/runs", tags=["Office"])


def _map_task_to_dto(task: TaskRecord) -> TaskRecordDTO:
    """Map an internal TaskRecord domain/app model to the TaskRecordDTO."""
    return TaskRecordDTO(
        id=task.id,
        run_id=task.run_id,
        agent_role=task.agent_role,
        task_type=task.task_type,
        title=task.title,
        status=task.status,
        started_at=task.started_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
        progress_details=task.progress_details,
        blocker=task.blocker,
        attempt_number=task.attempt_number,
        related_artifact_ids=task.related_artifact_ids,
    )


def _map_office_state_to_response(state: OfficeState) -> OfficeStateResponse:
    """Map an internal OfficeState model to the OfficeStateResponse DTO."""
    return OfficeStateResponse(
        run_id=state.run_id,
        project_id=state.project_id,
        run_status=state.run_status,
        current_stage=state.current_stage,
        employees=[
            OfficeEmployeeDTO(
                role=e.role,
                name=e.name,
                title=e.title,
                avatar=e.avatar,
                workstation=e.workstation,
                status=e.status,
                active_task_id=e.active_task_id,
                current_activity=e.current_activity,
                last_active_at=e.last_active_at,
                is_logical_role=e.is_logical_role,
                completed_steps_count=e.completed_steps_count,
            )
            for e in state.employees
        ],
        workstations=[
            WorkstationDTO(
                id=w.id,
                name=w.name,
                description=w.description,
                assigned_role=w.assigned_role,
                active_task_id=w.active_task_id,
                queued_task_ids=w.queued_task_ids,
                status=w.status,
            )
            for w in state.workstations
        ],
        tasks=[_map_task_to_dto(t) for t in state.tasks],
        active_task_id=state.active_task_id,
        blockers=state.blockers,
        updated_at=state.updated_at,
    )


@router.get(
    "/{run_id}/office-state",
    status_code=status.HTTP_200_OK,
    response_model=OfficeStateResponse,
    dependencies=[Depends(get_api_key), Depends(limit_read_ops)],
)
async def get_office_state(
    run_id: str,
    office_service: Annotated[OfficeStateService, Depends(get_office_state_service)],
) -> OfficeStateResponse:
    """Retrieve the authoritative virtual office snapshot for a specific run."""
    state = office_service.get_office_state(run_id=run_id)
    return _map_office_state_to_response(state)


@router.get(
    "/{run_id}/tasks",
    status_code=status.HTTP_200_OK,
    response_model=ListTasksResponse,
    dependencies=[Depends(get_api_key), Depends(limit_read_ops)],
)
async def get_run_tasks(
    run_id: str,
    office_service: Annotated[OfficeStateService, Depends(get_office_state_service)],
) -> ListTasksResponse:
    """Retrieve all assigned tasks and their execution statuses for a specific run."""
    tasks = office_service.get_run_tasks(run_id=run_id)
    dtos = [_map_task_to_dto(t) for t in tasks]
    return ListTasksResponse(items=dtos, total=len(dtos))
