"""API tests for virtual office state and task endpoints."""

from fastapi.testclient import TestClient

from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from tests.api.conftest import APITestHarness


def test_get_office_state_success(client: TestClient, harness: APITestHarness) -> None:
    """GET /api/v1/runs/{run_id}/office-state returns structured snapshot."""
    run = Run(
        run_id="run-api-office-1", project_id="proj-office-1", state=RunState.PLANNING
    )
    harness.repository.save(run)

    response = client.get(f"/api/v1/runs/{run.run_id}/office-state")
    assert response.status_code == 200

    data = response.json()
    assert data["run_id"] == "run-api-office-1"
    assert data["project_id"] == "proj-office-1"
    assert data["run_status"] == "PLANNING"
    assert data["current_stage"] == "planning"

    assert len(data["employees"]) == 7
    assert len(data["workstations"]) == 7
    assert len(data["tasks"]) == 7

    # Check PM employee is working
    pm = next(e for e in data["employees"] if e["role"] == "pm")
    assert pm["status"] == "working"
    assert pm["workstation"] == "planning_desk"

    # Check planning workstation is active
    station = next(w for w in data["workstations"] if w["id"] == "planning_desk")
    assert station["status"] == "active"


def test_get_office_state_not_found(client: TestClient) -> None:
    """Non-existent run returns 404."""
    response = client.get("/api/v1/runs/non-existent-run-id/office-state")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data


def test_get_run_tasks_success(client: TestClient, harness: APITestHarness) -> None:
    """GET /api/v1/runs/{run_id}/tasks returns list of tasks."""
    run = Run(
        run_id="run-api-tasks-1",
        project_id="proj-tasks-1",
        state=RunState.AWAITING_APPROVAL,
    )
    harness.repository.save(run)

    response = client.get(f"/api/v1/runs/{run.run_id}/tasks")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 7
    assert len(data["items"]) == 7

    # Review task should be waiting_approval
    review_task = next(t for t in data["items"] if t["task_type"] == "approval")
    assert review_task["status"] == "waiting_approval"


def test_get_run_tasks_not_found(client: TestClient) -> None:
    """Non-existent run returns 404."""
    response = client.get("/api/v1/runs/non-existent-run-id/tasks")
    assert response.status_code == 404
