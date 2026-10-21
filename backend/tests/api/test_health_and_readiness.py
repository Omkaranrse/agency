"""Tests for /health and /ready endpoints, validation, and error safety."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from agency.interfaces.api.app import create_app
from agency.interfaces.api.config import APISettings
from agency.interfaces.api.dependencies import (
    set_run_repository,
    set_workflow_runner,
)
from tests.fakes.fake_run_repository import FakeRunRepository


@pytest.fixture
def api_client() -> TestClient:
    """Fixture providing initialized FastAPI test client."""
    settings = APISettings(env="development", allow_unauthenticated=True)
    app = create_app(settings)
    repo = FakeRunRepository()
    set_run_repository(repo)

    mock_runner = MagicMock()
    mock_runner.is_ready = True
    set_workflow_runner(mock_runner)

    return TestClient(app)


def test_health_endpoint_returns_ok(api_client: TestClient) -> None:
    """Health endpoint must return status ok with UTC timestamp."""
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    # No sensitive connection strings or passwords exposed
    assert "password" not in response.text.lower()
    assert "secret" not in response.text.lower()


def test_readiness_endpoint_succeeds_when_dependencies_healthy(
    api_client: TestClient,
) -> None:
    """Readiness returns 200 when repository and workflow runner are healthy."""
    response = api_client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["components"]["persistence"] == "ok"
    assert data["components"]["workflow_runner"] == "ready"


def test_readiness_fails_503_when_persistence_offline(api_client: TestClient) -> None:
    """Readiness returns 503 Service Unavailable when persistence raises error."""
    mock_repo = MagicMock()
    mock_repo.list.side_effect = RuntimeError("Database connection timeout")
    set_run_repository(mock_repo)

    response = api_client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    # Structured error without stack traces
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
    # Raw exception message not leaked
    assert "Database connection timeout" not in data["error"]["message"]


def test_readiness_fails_503_when_workflow_runner_shutting_down(
    api_client: TestClient,
) -> None:
    """Readiness returns 503 when runner is draining / shutting down."""
    mock_runner = MagicMock()
    mock_runner.is_ready = False
    set_workflow_runner(mock_runner)

    response = api_client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
