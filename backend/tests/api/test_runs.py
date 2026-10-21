"""API tests for Run creation, listing, pagination, and retrieval."""

from fastapi.testclient import TestClient

from agency.domain.entities.run import Run
from tests.api.conftest import APITestHarness, make_sample_brief


def test_create_run_success(client: TestClient) -> None:
    """Valid client brief returns 202 Accepted with initialized run metadata."""
    payload = {
        "brief": {
            "client_name": "Elena Rostova",
            "site_type": "Architectural Portfolio",
            "pages": ["Home", "About", "Projects", "Contact"],
            "tone": "Minimalist, refined",
            "content_notes": "Civic mass timber architecture projects.",
        },
        "project_id": "elena-arch",
    }

    response = client.post("/api/v1/runs", json=payload)
    assert response.status_code == 202

    data = response.json()
    assert "run_id" in data
    assert data["project_id"] == "elena-arch"
    assert data["status"] in ("CREATED", "PLANNING", "PROTOTYPING", "AWAITING_APPROVAL")
    assert "created_at" in data


def test_create_run_invalid_brief_returns_422(client: TestClient) -> None:
    """Malformed or empty brief fields return 422 with structured error details."""
    payload = {
        "brief": {
            "client_name": "",  # Empty name rejected
            "site_type": "Portfolio",
            "pages": [],  # Empty pages list rejected
            "tone": "Refined",
            "content_notes": "Notes",
        }
    }

    response = client.post("/api/v1/runs", json=payload)
    assert response.status_code == 422

    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "errors" in body["error"]["details"]
    assert len(body["error"]["details"]["errors"]) >= 1


def test_create_run_unknown_fields_rejected(client: TestClient) -> None:
    """Unknown fields in request payload are rejected with 422."""
    payload = {
        "brief": {
            "client_name": "Elena Rostova",
            "site_type": "Architectural Portfolio",
            "pages": ["Home"],
            "tone": "Minimalist",
            "content_notes": "Notes",
        },
        "unknown_extra_param": "malicious_payload",
    }

    response = client.post("/api/v1/runs", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_run_idempotency_key_deduplication(
    client: TestClient, harness: APITestHarness
) -> None:
    """Retrying run creation with the same idempotency key deduplicates."""
    payload = {
        "brief": {
            "client_name": "Elena Rostova",
            "site_type": "Architectural Portfolio",
            "pages": ["Home"],
            "tone": "Refined",
            "content_notes": "Notes",
        },
        "idempotency_key": "idemp-key-create-001",
    }

    res1 = client.post("/api/v1/runs", json=payload)
    assert res1.status_code == 202
    run_id1 = res1.json()["run_id"]
    assert run_id1 is not None

    res2 = client.post("/api/v1/runs", json=payload)
    assert res2.status_code == 202

    # Verify idempotency key is tracked in runner
    assert harness.runner.has_idempotency_key("idemp-key-create-001")


def test_list_runs_pagination_and_filtering(
    client: TestClient, harness: APITestHarness
) -> None:
    """List runs returns paginated items with total count and supports pagination."""
    brief = make_sample_brief()
    for i in range(5):
        run = Run(run_id=f"run-list-{i}", project_id=f"proj-{i}", brief=brief)
        harness.repository.save(run)

    response = client.get("/api/v1/runs?limit=2&offset=1")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 2
    assert data["pagination"]["total"] >= 5
    assert data["pagination"]["limit"] == 2
    assert data["pagination"]["offset"] == 1
    assert data["pagination"]["has_next"] is True


def test_get_run_by_id(client: TestClient, harness: APITestHarness) -> None:
    """Retrieve existing run returns full DTO summary."""
    brief = make_sample_brief()
    run = Run(run_id="run-detail-1", project_id="elena-detail", brief=brief)
    run.start_planning()
    harness.repository.save(run)

    response = client.get("/api/v1/runs/run-detail-1")
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == "run-detail-1"
    assert data["project_id"] == "elena-detail"
    assert data["status"] == "PLANNING"
    assert "created_at" in data
    assert "updated_at" in data


def test_get_run_not_found(client: TestClient) -> None:
    """Requesting non-existent run returns 404 with consistent error format."""
    response = client.get("/api/v1/runs/non-existent-run-999")
    assert response.status_code == 404

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RUN_NOT_FOUND"
    assert "non-existent-run-999" in data["error"]["message"]
    assert "X-Request-ID" in response.headers
