"""FastAPI application factory, lifespan management, middleware, and route mounting."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from agency.interfaces.api.config import APISettings
from agency.interfaces.api.dependencies import (
    get_run_repository,
    get_workflow_runner,
    init_default_dependencies,
    set_settings,
)
from agency.interfaces.api.errors import setup_exception_handlers
from agency.interfaces.api.middleware import (
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
)
from agency.interfaces.api.routers import (
    approvals_router,
    artifacts_router,
    events_router,
    office_router,
    runs_router,
)
from agency.interfaces.api.schemas.common import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application resource startup and deterministic shutdown."""
    yield

    # Clean shutdown of background task runner
    try:
        runner = get_workflow_runner()
        await runner.shutdown()
    except Exception:
        pass


def create_app(settings: APISettings | None = None) -> FastAPI:
    """Construct and configure the Agency FastAPI application."""
    effective_settings = settings or APISettings()
    set_settings(effective_settings)
    init_default_dependencies(effective_settings)

    app = FastAPI(
        title="Agency API",
        description=(
            "Multi-agent software delivery agency REST API and event streaming."
        ),
        version="0.1.0",
        docs_url="/docs" if not effective_settings.is_production else None,
        redoc_url="/redoc" if not effective_settings.is_production else None,
        lifespan=lifespan,
    )

    # 1. Mount custom middleware in correct onion order
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_size_bytes=effective_settings.max_request_body_size,
    )

    # 2. Configure strict CORS
    # Disallow wildcard when credentials are true
    origins = [orig for orig in effective_settings.dashboard_origins if orig != "*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-API-Key",
            "X-Request-ID",
            "Last-Event-ID",
        ],
        expose_headers=["X-Request-ID"],
    )

    # 3. Register centralized exception handlers
    setup_exception_handlers(app)

    # 4. Mount versioned API routes under /api/v1
    api_v1_prefix = "/api/v1"
    app.include_router(runs_router, prefix=api_v1_prefix)
    app.include_router(office_router, prefix=api_v1_prefix)
    app.include_router(approvals_router, prefix=api_v1_prefix)
    app.include_router(events_router, prefix=api_v1_prefix)
    app.include_router(artifacts_router, prefix=api_v1_prefix)

    # 5. Operational endpoints
    @app.get("/", tags=["Root"])
    async def root_index() -> dict[str, str]:
        return {
            "name": "Agency API",
            "version": "0.1.0",
            "status": "online",
            "docs_url": "/docs",
            "health_url": "/health",
            "readiness_url": "/ready",
        }

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/ready", response_model=HealthResponse, tags=["Health"])
    async def readiness_check() -> HealthResponse:
        components: dict[str, str] = {}
        all_ready = True

        # 1. Verify required persistence
        try:
            repo = get_run_repository()
            repo.list(limit=1, offset=0)
            components["persistence"] = "ok"
        except Exception:
            components["persistence"] = "unavailable"
            all_ready = False

        # 2. Verify workflow execution infrastructure
        try:
            runner = get_workflow_runner()
            if runner.is_ready:
                components["workflow_runner"] = "ready"
            else:
                components["workflow_runner"] = "shutting_down"
                all_ready = False
        except Exception:
            components["workflow_runner"] = "unavailable"
            all_ready = False

        # 3. Optional telemetry status (does not block readiness)
        components["telemetry"] = "optional_available"

        if not all_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Required application dependencies are unavailable.",
                    "components": components,
                },
            )

        return HealthResponse(status="ready", components=components)

    return app
