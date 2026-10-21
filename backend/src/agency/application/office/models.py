"""Application models for virtual office visualization and agent task tracking."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AgentRoleEnum(StrEnum):
    """Logical agent and operator roles represented in the virtual office."""

    MANAGER = "manager"
    PM = "pm"
    DESIGNER = "designer"
    BUILDER = "builder"
    QA = "qa"
    REVIEWER = "reviewer"
    DEVOPS = "devops"


class WorkstationEnum(StrEnum):
    """Physical office workstation zones corresponding to workflow stages."""

    MANAGER_DESK = "manager_desk"
    PLANNING_DESK = "planning_desk"
    DESIGN_STATION = "design_station"
    DEVELOPMENT_STATION = "development_station"
    QA_STATION = "qa_station"
    REVIEW_AREA = "review_area"
    OPERATIONS_STATION = "operations_station"


class EmployeeStatusEnum(StrEnum):
    """Operational status of an employee character in the office."""

    IDLE = "idle"
    WALKING = "walking"
    WORKING = "working"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED = "blocked"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatusEnum(StrEnum):
    """Lifecycle states of an agent's assigned task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskRecord(BaseModel):
    """Record of an individual task assigned to a team member in a run."""

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


class OfficeEmployeeState(BaseModel):
    """Current visual, operational, and assignment state of an office employee."""

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


class WorkstationState(BaseModel):
    """Zone state and queued/active work items at an office workstation."""

    model_config = ConfigDict(extra="forbid")

    id: WorkstationEnum
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=250)
    assigned_role: AgentRoleEnum
    active_task_id: str | None = None
    queued_task_ids: list[str] = Field(default_factory=list)
    status: str = Field(min_length=1, max_length=50)


class OfficeState(BaseModel):
    """Authoritative snapshot of the virtual office for a run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=100)
    project_id: str = Field(min_length=1, max_length=100)
    run_status: str = Field(min_length=1, max_length=50)
    current_stage: str = Field(min_length=1, max_length=50)
    employees: list[OfficeEmployeeState] = Field(default_factory=list)
    workstations: list[WorkstationState] = Field(default_factory=list)
    tasks: list[TaskRecord] = Field(default_factory=list)
    active_task_id: str | None = None
    blockers: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
