"""FastAPI dependency injection providers for configuration, auth,
rate limiting, and services.
"""

import hmac
import time
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request

if TYPE_CHECKING:
    from agency.application.office.service import OfficeStateService

from agency.application.ports.artifact_storage import ArtifactStoragePort
from agency.application.ports.event_bus import EventBusPort
from agency.application.ports.event_feed import EventFeedPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.application.services.workflow_runner import WorkflowRunner
from agency.interfaces.api.config import APISettings

# Singleton settings holder
_settings = APISettings()


def get_settings() -> APISettings:
    """Return current API settings."""
    return _settings


def set_settings(settings: APISettings) -> None:
    """Override API settings for testing."""
    global _settings
    _settings = settings


# --- Authentication Dependency ---


async def get_api_key(
    request: Request,
    settings: Annotated[APISettings, Depends(get_settings)],
) -> str:
    """Validate API key via constant-time comparison or allow unauthenticated in dev."""
    # Production fail-closed guarantee
    if settings.is_production and not settings.api_key:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "SECURITY_CONFIGURATION_ERROR",
                "message": "API key configuration is required in production.",
            },
        )

    # Allow unauthenticated in dev if explicitly enabled
    if settings.allow_unauthenticated and not settings.is_production:
        return "development-unauthenticated"

    # Extract key from X-API-Key header or Authorization: Bearer <key>
    api_key_header = request.headers.get("X-API-Key")
    auth_header = request.headers.get("Authorization")

    provided_key: str | None = None
    if api_key_header:
        provided_key = api_key_header.strip()
    elif auth_header and auth_header.lower().startswith("bearer "):
        provided_key = auth_header[7:].strip()

    if not provided_key or not settings.api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Missing or invalid API key credentials.",
            },
        )

    # Constant-time comparison
    if not hmac.compare_digest(provided_key, settings.api_key):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Missing or invalid API key credentials.",
            },
        )

    return provided_key


# --- In-Memory Sliding-Window Rate Limiter ---


class InMemoryRateLimiter:
    """In-memory sliding window rate limiter tracking requests per client."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(
        self, client_key: str, max_requests: int, window_seconds: float
    ) -> bool:
        now = time.time()
        window_start = now - window_seconds

        # Prune old timestamps
        history = [ts for ts in self._requests[client_key] if ts > window_start]
        self._requests[client_key] = history

        if len(history) >= max_requests:
            return False

        self._requests[client_key].append(now)
        return True

    def clear(self) -> None:
        """Clear all recorded request timestamps."""
        self._requests.clear()


_rate_limiter = InMemoryRateLimiter()


def get_rate_limiter() -> InMemoryRateLimiter:
    """Return the active rate limiter."""
    return _rate_limiter


def rate_limit(
    max_requests_func: Callable[[APISettings], int],
) -> Callable[..., None]:
    """Factory creating rate limiting dependencies for route handlers."""

    def _limiter_dependency(
        request: Request,
        settings: Annotated[APISettings, Depends(get_settings)],
        limiter: Annotated[InMemoryRateLimiter, Depends(get_rate_limiter)],
    ) -> None:
        # Determine client identity (IP or API key)
        client_key = request.headers.get("X-API-Key") or (
            request.client.host if request.client else "127.0.0.1"
        )
        max_requests = max_requests_func(settings)

        if not limiter.is_allowed(
            client_key=client_key,
            max_requests=max_requests,
            window_seconds=float(settings.rate_limit_window_seconds),
        ):
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": (
                        f"Rate limit of {max_requests} requests per "
                        f"{settings.rate_limit_window_seconds}s exceeded."
                    ),
                },
            )

    return _limiter_dependency


# Pre-configured rate limiting dependencies
limit_create_runs = rate_limit(lambda s: s.rate_limit_creates_per_minute)
limit_write_ops = rate_limit(lambda s: s.rate_limit_writes_per_minute)
limit_read_ops = rate_limit(lambda s: s.rate_limit_reads_per_minute)


# --- Composition Root / Service Dependencies ---

_repository: RunRepositoryPort | None = None
_event_feed: EventFeedPort | None = None
_artifact_storage: ArtifactStoragePort | None = None
_workflow_runner: WorkflowRunner | None = None


def init_default_dependencies(settings: APISettings | None = None) -> None:
    """Initialize default dependencies for standalone API server execution."""
    global _repository, _event_feed, _artifact_storage, _workflow_runner, _event_bus
    effective_settings = settings or _settings

    if _repository is None:
        from agency.infrastructure.persistence.in_memory_run_repository import (
            InMemoryRunRepository,
        )

        _repository = InMemoryRunRepository()

    if _event_feed is None:
        from agency.infrastructure.persistence.durable_event_feed import (
            DurableEventFeed,
        )

        _event_feed = DurableEventFeed()

    if _event_bus is None:
        from agency.domain.events import DomainEvent
        from agency.infrastructure.persistence.broadcasting_event_bus import (
            BroadcastingEventBus,
        )

        class _NoOpBus(EventBusPort):
            def publish(self, event: DomainEvent) -> None:
                pass

            def publish_all(self, events: list[DomainEvent]) -> None:
                pass

        _event_bus = BroadcastingEventBus(
            event_feed=_event_feed,
            delegate_bus=_NoOpBus(),
        )

    if _artifact_storage is None:
        from agency.infrastructure.persistence.local_artifact_storage import (
            LocalArtifactStorage,
        )

        _artifact_storage = LocalArtifactStorage(
            base_dir=effective_settings.artifacts_dir
        )

    if _workflow_runner is None:
        from tests.fakes.fake_deploy import FakeDeploy
        from tests.fakes.fake_qa_service import FakeQAService
        from tests.fakes.fake_sandbox import FakeSandbox

        from agency.application.agents.builder_agent import BuilderAgent
        from agency.application.agents.designer_agent import DesignerAgent
        from agency.application.agents.pm_agent import PMAgent
        from agency.application.graph.graph_service import WorkflowGraphService
        from agency.application.graph.nodes import GraphNodes
        from agency.infrastructure.llm.routing_llm import RoutingLLM
        from agency.infrastructure.persistence.langgraph_checkpointer import (
            create_in_memory_checkpointer,
        )

        llm = RoutingLLM()
        nodes = GraphNodes(
            repository=_repository,
            event_bus=_event_bus,
            pm_agent=PMAgent(llm=llm),
            designer_agent=DesignerAgent(llm=llm),
            builder_agent=BuilderAgent(llm=llm),
            qa_service=FakeQAService(),
            sandbox=FakeSandbox(),
            deploy_port=FakeDeploy(),
        )
        checkpointer = create_in_memory_checkpointer()
        workflow_service = WorkflowGraphService(nodes=nodes, checkpointer=checkpointer)
        _workflow_runner = WorkflowRunner(workflow_service=workflow_service)


def get_run_repository() -> RunRepositoryPort:
    """Return the active RunRepositoryPort."""
    if _repository is None:
        init_default_dependencies()
    assert _repository is not None
    return _repository


def set_run_repository(repo: RunRepositoryPort) -> None:
    """Set the active RunRepositoryPort (for app factory or testing)."""
    global _repository
    _repository = repo


def get_event_feed() -> EventFeedPort:
    """Return the active EventFeedPort."""
    if _event_feed is None:
        init_default_dependencies()
    assert _event_feed is not None
    return _event_feed


def set_event_feed(feed: EventFeedPort) -> None:
    """Set the active EventFeedPort."""
    global _event_feed
    _event_feed = feed


def get_artifact_storage() -> ArtifactStoragePort:
    """Return the active ArtifactStoragePort."""
    if _artifact_storage is None:
        init_default_dependencies()
    assert _artifact_storage is not None
    return _artifact_storage


def set_artifact_storage(storage: ArtifactStoragePort) -> None:
    """Set the active ArtifactStoragePort."""
    global _artifact_storage
    _artifact_storage = storage


def get_workflow_runner() -> WorkflowRunner:
    """Return the active WorkflowRunner supervisor."""
    if _workflow_runner is None:
        init_default_dependencies()
    assert _workflow_runner is not None
    return _workflow_runner


def set_workflow_runner(runner: WorkflowRunner) -> None:
    """Set the active WorkflowRunner."""
    global _workflow_runner
    _workflow_runner = runner


_event_bus: EventBusPort | None = None


def get_event_bus() -> EventBusPort:
    """Return the active EventBusPort."""
    if _event_bus is None:
        init_default_dependencies()
    assert _event_bus is not None
    return _event_bus


def set_event_bus(bus: EventBusPort) -> None:
    """Set the active EventBusPort."""
    global _event_bus
    _event_bus = bus


def get_office_state_service(
    repository: Annotated[RunRepositoryPort, Depends(get_run_repository)],
    event_feed: Annotated[EventFeedPort, Depends(get_event_feed)],
    artifact_storage: Annotated[ArtifactStoragePort, Depends(get_artifact_storage)],
) -> "OfficeStateService":
    """Return an OfficeStateService instance wired to active repository
    and event feed.
    """
    from agency.application.office.service import OfficeStateService

    return OfficeStateService(
        repository=repository,
        event_feed=event_feed,
        artifact_storage=artifact_storage,
    )
