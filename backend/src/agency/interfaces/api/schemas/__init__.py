"""API Request and Response Data Transfer Object (DTO) schemas."""

from agency.interfaces.api.schemas.approvals import (
    ApproveRunRequest,
    ApproveRunResponse,
    CancelRunRequest,
    CancelRunResponse,
    ReviseRunRequest,
    ReviseRunResponse,
)
from agency.interfaces.api.schemas.artifacts import (
    ArtifactMetadataDTO,
    ListArtifactsResponse,
)
from agency.interfaces.api.schemas.common import (
    APIErrorResponse,
    ErrorBody,
    HealthResponse,
    PaginationMeta,
)
from agency.interfaces.api.schemas.events import EventDTO
from agency.interfaces.api.schemas.office import (
    ListTasksResponse,
    OfficeEmployeeDTO,
    OfficeStateResponse,
    TaskRecordDTO,
    WorkstationDTO,
)
from agency.interfaces.api.schemas.runs import (
    BriefDTO,
    CreateRunRequest,
    CreateRunResponse,
    ListRunsResponse,
    RunResponse,
)

__all__ = [
    "APIErrorResponse",
    "ApproveRunRequest",
    "ApproveRunResponse",
    "ArtifactMetadataDTO",
    "BriefDTO",
    "CancelRunRequest",
    "CancelRunResponse",
    "CreateRunRequest",
    "CreateRunResponse",
    "ErrorBody",
    "EventDTO",
    "HealthResponse",
    "ListArtifactsResponse",
    "ListRunsResponse",
    "ListTasksResponse",
    "OfficeEmployeeDTO",
    "OfficeStateResponse",
    "PaginationMeta",
    "ReviseRunRequest",
    "ReviseRunResponse",
    "RunResponse",
    "TaskRecordDTO",
    "WorkstationDTO",
]
