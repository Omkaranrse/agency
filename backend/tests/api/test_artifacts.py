"""API tests for artifact listing, secure downloading, and path traversal prevention."""

from fastapi.testclient import TestClient

from agency.domain.entities.run import Run
from tests.api.conftest import APITestHarness, make_sample_brief


def test_list_artifacts_success(client: TestClient, harness: APITestHarness) -> None:
    """Artifact listing returns safe metadata for all approved artifacts."""
    brief = make_sample_brief()
    run = Run(run_id="run-art-1", project_id="elena-art", brief=brief)
    harness.repository.save(run)

    # Save artifacts into storage
    harness.artifact_storage.save_artifact(
        run_id="run-art-1",
        artifact_id="spec.json",
        artifact_type="spec",
        display_name="Specification Document",
        mime_type="application/json",
        content=b'{"title": "Elena Rostova Portfolio"}',
    )
    harness.artifact_storage.save_artifact(
        run_id="run-art-1",
        artifact_id="tokens.css",
        artifact_type="tokens",
        display_name="Design Tokens",
        mime_type="text/css",
        content=b":root { --color-primary: #9C4126; }",
    )

    response = client.get("/api/v1/runs/run-art-1/artifacts")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    types = [item["artifact_type"] for item in data["items"]]
    assert "spec" in types
    assert "tokens" in types


def test_list_artifacts_unknown_run_returns_404(client: TestClient) -> None:
    """Listing artifacts for unknown run returns 404."""
    response = client.get("/api/v1/runs/non-existent-art-run/artifacts")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RUN_NOT_FOUND"


def test_get_artifact_content_and_safe_headers(
    client: TestClient, harness: APITestHarness
) -> None:
    """Retrieving an artifact serves raw content with safe isolated download headers."""
    brief = make_sample_brief()
    run = Run(run_id="run-art-2", project_id="elena-art-2", brief=brief)
    harness.repository.save(run)

    harness.artifact_storage.save_artifact(
        run_id="run-art-2",
        artifact_id="tokens.css",
        artifact_type="tokens",
        display_name="tokens.css",
        mime_type="text/css",
        content=b":root { --brand: #9C4126; }",
    )

    response = client.get("/api/v1/runs/run-art-2/artifacts/tokens.css")
    assert response.status_code == 200
    assert response.content == b":root { --brand: #9C4126; }"
    assert "text/css" in response.headers["content-type"]
    disposition = response.headers["content-disposition"]
    assert 'attachment; filename="tokens.css"' in disposition
    assert response.headers["x-content-type-options"] == "nosniff"


def test_get_artifact_not_found(client: TestClient, harness: APITestHarness) -> None:
    """Requesting missing artifact ID returns 404 ARTIFACT_NOT_FOUND."""
    brief = make_sample_brief()
    run = Run(run_id="run-art-3", project_id="elena-art-3", brief=brief)
    harness.repository.save(run)

    response = client.get("/api/v1/runs/run-art-3/artifacts/missing.json")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ARTIFACT_NOT_FOUND"


def test_get_artifact_path_traversal_attempt_rejected(
    client: TestClient, harness: APITestHarness
) -> None:
    """Path traversal sequences (e.g. ..) in artifact ID are rejected."""
    brief = make_sample_brief()
    run = Run(run_id="run-art-4", project_id="elena-art-4", brief=brief)
    harness.repository.save(run)

    response = client.get("/api/v1/runs/run-art-4/artifacts/..%2F..%2Fetc%2Fpasswd")
    # Should be rejected with 403, 404, or 400
    assert response.status_code in (403, 404, 400)
