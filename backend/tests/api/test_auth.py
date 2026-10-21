"""API tests for API-key authentication, production fail-closed security, and CORS."""

from fastapi.testclient import TestClient

from agency.interfaces.api.app import create_app
from agency.interfaces.api.config import APISettings
from tests.api.conftest import TEST_API_KEY, APITestHarness


def test_missing_api_key_returns_401(harness: APITestHarness) -> None:
    """Request without API credentials returns 401 with standard error format."""
    with TestClient(harness.app) as c:
        response = c.get("/api/v1/runs")
        assert response.status_code == 401

        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "UNAUTHORIZED"
        assert "credentials" in data["error"]["message"].lower()


def test_invalid_api_key_returns_401(harness: APITestHarness) -> None:
    """Request with incorrect API key returns 401."""
    with TestClient(harness.app, headers={"X-API-Key": "wrong-key-xyz"}) as c:
        response = c.get("/api/v1/runs")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_valid_api_key_via_x_api_key_header(harness: APITestHarness) -> None:
    """Request with valid X-API-Key succeeds with 200."""
    with TestClient(harness.app, headers={"X-API-Key": TEST_API_KEY}) as c:
        response = c.get("/api/v1/runs")
        assert response.status_code == 200


def test_valid_api_key_via_authorization_bearer(harness: APITestHarness) -> None:
    """Request with valid Authorization: Bearer <key> succeeds with 200."""
    with TestClient(
        harness.app, headers={"Authorization": f"Bearer {TEST_API_KEY}"}
    ) as c:
        response = c.get("/api/v1/runs")
        assert response.status_code == 200


def test_health_endpoints_accessible_without_auth(harness: APITestHarness) -> None:
    """Operational health and readiness checks do not require authentication."""
    with TestClient(harness.app) as c:
        res_health = c.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "ok"

        res_ready = c.get("/ready")
        assert res_ready.status_code == 200
        assert res_ready.json()["status"] == "ready"


def test_production_mode_fails_closed_when_key_unconfigured() -> None:
    """Missing configured API key in production causes a 500 configuration error."""
    prod_settings = APISettings(env="production", api_key=None)
    prod_app = create_app(prod_settings)

    with TestClient(prod_app) as c:
        response = c.get("/api/v1/runs")
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "SECURITY_CONFIGURATION_ERROR"


def test_cors_allowlisted_origin_accepted(harness: APITestHarness) -> None:
    """Pre-flight request from allowlisted dashboard origin returns allowed origin."""
    with TestClient(harness.app) as c:
        response = c.options(
            "/api/v1/runs",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-API-Key, Content-Type",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )


def test_cors_disallowed_origin_rejected(harness: APITestHarness) -> None:
    """Request from unallowlisted origin does not reflect allowed origin header."""
    with TestClient(harness.app) as c:
        response = c.options(
            "/api/v1/runs",
            headers={
                "Origin": "https://malicious-website.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert (
            response.headers.get("access-control-allow-origin")
            != "https://malicious-website.com"
        )
