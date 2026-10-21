"""API router packages exporting all endpoint groups."""

from agency.interfaces.api.routers.approvals import router as approvals_router
from agency.interfaces.api.routers.artifacts import router as artifacts_router
from agency.interfaces.api.routers.events import router as events_router
from agency.interfaces.api.routers.office import router as office_router
from agency.interfaces.api.routers.runs import router as runs_router

__all__ = [
    "approvals_router",
    "artifacts_router",
    "events_router",
    "office_router",
    "runs_router",
]
