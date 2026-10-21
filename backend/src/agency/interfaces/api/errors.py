"""Centralized exception handlers mapping domain/application errors to
standard API responses.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from agency.application.errors import (
    ArtifactAccessDeniedError,
    ArtifactNotFoundError,
    InvalidRequestError,
    RevisionLimitExceededError,
    RunNotFoundError,
)
from agency.application.graph.errors import (
    ApprovalValidationError,
    StaleApprovalError,
    WorkflowCancelledError,
)
from agency.domain.errors import (
    InvalidApprovalError,
    InvalidRevisionRequestError,
    InvalidStateTransitionError,
)

logger = logging.getLogger(__name__)


def _make_error_response(
    status_code: int,
    code: str,
    message: str,
    request: Request,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "unknown")
    content = {
        "error": {
            "code": code,
            "message": message,
            "request_id": req_id,
            "details": details or {},
        }
    }
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={"X-Request-ID": req_id},
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register all centralized exception handlers on the FastAPI application."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = "HTTP_ERROR"
        message = str(exc.detail)
        details: dict[str, Any] = {}

        if isinstance(exc.detail, dict):
            code = str(exc.detail.get("code", "HTTP_ERROR"))
            message = str(exc.detail.get("message", exc.detail))
            details = {
                k: v for k, v in exc.detail.items() if k not in ("code", "message")
            }

        return _make_error_response(
            status_code=exc.status_code,
            code=code,
            message=message,
            request=request,
            details=details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Sanitize error representations
        errors = []
        for err in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in err.get("loc", [])),
                    "message": err.get("msg", "Invalid field"),
                    "type": err.get("type", "value_error"),
                }
            )

        return _make_error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            request=request,
            details={"errors": errors},
        )

    @app.exception_handler(RunNotFoundError)
    async def run_not_found_handler(
        request: Request, exc: RunNotFoundError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=404,
            code="RUN_NOT_FOUND",
            message=exc.message,
            request=request,
            details={"run_id": exc.run_id},
        )

    @app.exception_handler(ArtifactNotFoundError)
    async def artifact_not_found_handler(
        request: Request, exc: ArtifactNotFoundError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=404,
            code="ARTIFACT_NOT_FOUND",
            message=exc.message,
            request=request,
            details={"run_id": exc.run_id, "artifact_id": exc.artifact_id},
        )

    @app.exception_handler(ArtifactAccessDeniedError)
    async def artifact_access_denied_handler(
        request: Request, exc: ArtifactAccessDeniedError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=403,
            code="ARTIFACT_ACCESS_DENIED",
            message=exc.message,
            request=request,
        )

    @app.exception_handler(StaleApprovalError)
    async def stale_approval_handler(
        request: Request, exc: StaleApprovalError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=409,
            code="STALE_APPROVAL",
            message=str(exc),
            request=request,
        )

    @app.exception_handler(InvalidApprovalError)
    async def invalid_approval_handler(
        request: Request, exc: InvalidApprovalError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=409,
            code="INVALID_APPROVAL_STATE",
            message=exc.reason,
            request=request,
            details={"run_id": exc.run_id},
        )

    @app.exception_handler(InvalidRevisionRequestError)
    async def invalid_revision_handler(
        request: Request, exc: InvalidRevisionRequestError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=409,
            code="INVALID_REVISION_STATE",
            message=exc.reason,
            request=request,
            details={"run_id": exc.run_id},
        )

    @app.exception_handler(RevisionLimitExceededError)
    async def revision_limit_handler(
        request: Request, exc: RevisionLimitExceededError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=409,
            code="REVISION_LIMIT_EXCEEDED",
            message=exc.message,
            request=request,
            details={"run_id": exc.run_id, "max_revisions": exc.max_revisions},
        )

    @app.exception_handler(InvalidStateTransitionError)
    async def invalid_transition_handler(
        request: Request, exc: InvalidStateTransitionError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=409,
            code="INVALID_STATE_TRANSITION",
            message=exc.message,
            request=request,
            details={
                "from_state": exc.from_state.value,
                "to_state": exc.to_state.value,
            },
        )

    @app.exception_handler(ApprovalValidationError)
    async def approval_validation_handler(
        request: Request, exc: ApprovalValidationError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=400,
            code="INVALID_APPROVAL_REQUEST",
            message=str(exc),
            request=request,
        )

    @app.exception_handler(InvalidRequestError)
    async def invalid_request_handler(
        request: Request, exc: InvalidRequestError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=400,
            code="INVALID_REQUEST",
            message=exc.message,
            request=request,
        )

    @app.exception_handler(WorkflowCancelledError)
    async def workflow_cancelled_handler(
        request: Request, exc: WorkflowCancelledError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=409,
            code="WORKFLOW_CANCELLED",
            message=str(exc),
            request=request,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        req_id = getattr(request.state, "request_id", "unknown")
        logger.error(
            "Unhandled internal exception [request_id=%s]: %s",
            req_id,
            exc,
            exc_info=True,
        )
        return _make_error_response(
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
            request=request,
        )
