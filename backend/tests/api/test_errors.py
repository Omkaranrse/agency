"""API tests verifying centralized consistent error responses and security hygiene."""

from fastapi import APIRouter
from fastapi.testclient import TestClient

from tests.api.conftest import APITestHarness


def test_consistent_error_response_structure(client: TestClient) -> None:
    """Error responses consistently follow the APIErrorResponse specification."""
    response = client.get("/api/v1/runs/missing-id-999")
    assert response.status_code == 404

    data = response.json()
    assert "error" in data
    error = data["error"]
    assert "code" in error
    assert "message" in error
    assert "request_id" in error
    assert "details" in error
    assert error["code"] == "RUN_NOT_FOUND"


def test_unhandled_exception_does_not_leak_tracebacks(harness: APITestHarness) -> None:
    """Unhandled server errors return 500 without leaking stack traces or secrets."""
    faulty_router = APIRouter()

    @faulty_router.get("/api/v1/test-faulty-crash")
    async def crash_endpoint() -> None:
        raise RuntimeError("Internal database password=super_secret connection failed!")

    harness.app.include_router(faulty_router)

    with TestClient(harness.app, raise_server_exceptions=False) as c:
        response = c.get("/api/v1/test-faulty-crash")
        assert response.status_code == 500

        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert (
            data["error"]["message"] == "An unexpected internal server error occurred."
        )
        # Ensure raw secret in exception message was not exposed to the caller
        assert "super_secret" not in response.text
        assert "Traceback" not in response.text
