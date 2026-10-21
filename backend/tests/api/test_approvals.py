"""API tests for human approval, revision requests, and cancellation endpoints."""

from fastapi.testclient import TestClient

from agency.domain.entities.run import Run
from tests.api.conftest import APITestHarness, make_sample_brief


def test_approve_run_success(client: TestClient, harness: APITestHarness) -> None:
    """Valid approval on a run awaiting approval returns 200 with approved decision."""
    brief = make_sample_brief()
    run = Run(run_id="run-appr-1", project_id="elena-appr", brief=brief)
    run.start_planning()
    run.finish_planning()
    run.submit_prototype("preview-ref-0")
    harness.repository.save(run)

    response = client.post(
        "/api/v1/runs/run-appr-1/approve",
        json={"revision": 0, "approver": "client-elena"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == "run-appr-1"
    assert data["decision"] == "approved"
    assert data["revision"] == 0
    assert "recorded_at" in data


def test_approve_run_not_awaiting_approval_returns_409(
    client: TestClient, harness: APITestHarness
) -> None:
    """Attempting to approve a run in PLANNING returns 409 conflict."""
    brief = make_sample_brief()
    run = Run(run_id="run-appr-2", project_id="elena-appr-2", brief=brief)
    run.start_planning()
    harness.repository.save(run)

    response = client.post(
        "/api/v1/runs/run-appr-2/approve",
        json={"revision": 0, "approver": "client"},
    )
    assert response.status_code == 409

    body = response.json()
    assert body["error"]["code"] == "INVALID_APPROVAL_STATE"


def test_approve_run_stale_revision_returns_409(
    client: TestClient, harness: APITestHarness
) -> None:
    """Approval matching an outdated revision number returns 409 STALE_APPROVAL."""
    brief = make_sample_brief()
    run = Run(run_id="run-appr-3", project_id="elena-appr-3", brief=brief)
    run.start_planning()
    run.finish_planning()
    run.submit_prototype("preview-ref-0")
    run.request_revision("Adjust warmth")
    run.submit_prototype("preview-ref-1")
    assert run.revision_count == 1
    harness.repository.save(run)

    # Submit with stale revision 0
    response = client.post(
        "/api/v1/runs/run-appr-3/approve",
        json={"revision": 0, "approver": "client"},
    )
    assert response.status_code == 409

    body = response.json()
    assert body["error"]["code"] == "STALE_APPROVAL"


def test_revise_run_success(client: TestClient, harness: APITestHarness) -> None:
    """Submitting a valid revision request increments revision and returns 200."""
    brief = make_sample_brief()
    run = Run(run_id="run-rev-1", project_id="elena-rev-1", brief=brief)
    run.start_planning()
    run.finish_planning()
    run.submit_prototype("preview-ref-0")
    harness.repository.save(run)

    response = client.post(
        "/api/v1/runs/run-rev-1/revise",
        json={"revision": 0, "comment": "Make header font size larger."},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == "run-rev-1"
    assert data["decision"] == "revised"
    assert data["new_revision"] == 1
    assert data["comment"] == "Make header font size larger."


def test_revise_run_empty_comment_rejected_with_422(
    client: TestClient, harness: APITestHarness
) -> None:
    """Revision requests with empty or missing comment are rejected with 422."""
    brief = make_sample_brief()
    run = Run(run_id="run-rev-2", project_id="elena-rev-2", brief=brief)
    run.start_planning()
    run.finish_planning()
    run.submit_prototype("preview-ref-0")
    harness.repository.save(run)

    response = client.post(
        "/api/v1/runs/run-rev-2/revise",
        json={"revision": 0, "comment": ""},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_cancel_run_success(client: TestClient, harness: APITestHarness) -> None:
    """Cancelling an active run returns 200 with cancelled status."""
    brief = make_sample_brief()
    run = Run(run_id="run-cancel-1", project_id="elena-cancel-1", brief=brief)
    run.start_planning()
    harness.repository.save(run)

    response = client.post(
        "/api/v1/runs/run-cancel-1/cancel",
        json={"reason": "Client stopped contract"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == "run-cancel-1"
    assert data["status"] == "cancelled"
    assert data["reason"] == "Client stopped contract"


def test_cancel_run_idempotency(client: TestClient, harness: APITestHarness) -> None:
    """Cancelling an already cancelled run returns 200 idempotently."""
    brief = make_sample_brief()
    run = Run(run_id="run-cancel-2", project_id="elena-cancel-2", brief=brief)
    run.start_planning()
    run.cancel("First cancellation")
    harness.repository.save(run)

    response = client.post(
        "/api/v1/runs/run-cancel-2/cancel",
        json={"reason": "Second cancellation attempt"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
