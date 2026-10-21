"""API Data Transfer Objects for the virtual office and employee task tracking."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from agency.application.office.models import (
    AgentRoleEnum,
    EmployeeStatusEnum,
    TaskStatusEnum,
    WorkstationEnum,
)


class TaskRecordDTO(BaseModel):
    """External API response schema for a task record."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=100)
    run_id: str = Field(min_length=1, max_length=100)
    agent_role: AgentRoleEnum
    task_type: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    status: TaskStatusEnum
    started_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    progress_details: str | None = None
    blocker: str | None = None
    attempt_number: int = Field(default=1, ge=1)
    related_artifact_ids: list[str] = Field(default_factory=list)


class OfficeEmployeeDTO(BaseModel):
    """External API response schema for an employee in the virtual office."""

    model_config = ConfigDict(extra="forbid")

    role: AgentRoleEnum
    name: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=100)
    avatar: str = Field(min_length=1, max_length=100)
    workstation: WorkstationEnum
    status: EmployeeStatusEnum
    active_task_id: str | None = None
    current_activity: str | None = None
    last_active_at: datetime | None = None
    is_logical_role: bool = False
    completed_steps_count: int = Field(default=0, ge=0)


class WorkstationDTO(BaseModel):
    """External API response schema for a workstation zone."""

    model_config = ConfigDict(extra="forbid")

    id: WorkstationEnum
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=250)
    assigned_role: AgentRoleEnum
    active_task_id: str | None = None
    queued_task_ids: list[str] = Field(default_factory=list)
    status: str = Field(min_length=1, max_length=50)


class OfficeStateResponse(BaseModel):
    """External API response snapshot for the complete virtual office state."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=100)
    project_id: str = Field(min_length=1, max_length=100)
    run_status: str = Field(min_length=1, max_length=50)
    current_stage: str = Field(min_length=1, max_length=50)
    employees: list[OfficeEmployeeDTO] = Field(default_factory=list)
    workstations: list[WorkstationDTO] = Field(default_factory=list)
    tasks: list[TaskRecordDTO] = Field(default_factory=list)
    active_task_id: str | None = None
    blockers: list[str] = Field(default_factory=list)
    updated_at: datetime


class ListTasksResponse(BaseModel):
    """External API response schema for listing tasks of a run."""

    model_config = ConfigDict(extra="forbid")

    items: list[TaskRecordDTO] = Field(default_factory=list)
    total: int = Field(ge=0)
