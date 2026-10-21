"""Unit tests for CleanupService (idempotency, dry-run, and cleanup)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from tests.fakes.fake_run_repository import FakeRunRepository

from agency.application.services.cleanup_service import CleanupService
from agency.domain.entities.brief import Brief
from agency.domain.entities.run import Run
from agency.domain.enums import RunState


def sample_run(run_id: str, state: RunState) -> Run:
    """Create a Run entity in the requested state."""
    brief = Brief(
        client_name="Test",
        site_type="Portfolio",
        pages=["home"],
        tone="clean",
        content_notes="Notes",
    )
    return Run(
        run_id=run_id,
        project_id="test-proj",
        brief=brief,
        state=state,
    )


def test_cleanup_protects_active_runs(tmp_path: Path) -> None:
    """Containers associated with non-terminal runs must never be deleted."""
    repo = FakeRunRepository()
    active_run = sample_run(run_id="run-active-1", state=RunState.BUILDING)
    completed_run = sample_run(run_id="run-done-2", state=RunState.COMPLETED)
    repo.save(active_run)
    repo.save(completed_run)

    # Mock Docker containers
    mock_active_container = MagicMock()
    mock_active_container.id = "c_active_123456"
    mock_active_container.labels = {
        "agency.managed": "true",
        "agency.run_id": "run-active-1",
        "agency.sandbox_id": "sbx-active",
    }

    mock_abandoned_container = MagicMock()
    mock_abandoned_container.id = "c_abandoned_789"
    mock_abandoned_container.labels = {
        "agency.managed": "true",
        "agency.run_id": "run-done-2",
        "agency.sandbox_id": "sbx-done",
    }

    mock_docker = MagicMock()
    mock_docker.containers.list.return_value = [
        mock_active_container,
        mock_abandoned_container,
    ]

    service = CleanupService(
        repository=repo,
        docker_client=mock_docker,
        base_workspace_dir=tmp_path,
    )

    summary = service.run_cleanup(retention_hours=1.0, dry_run=False)

    assert summary.active_runs_protected == 1
    assert "c_active_123" not in summary.containers_removed
    assert "c_abandoned_" in summary.containers_removed[0]

    mock_abandoned_container.stop.assert_called_once()
    mock_abandoned_container.remove.assert_called_once_with(force=True)
    mock_active_container.stop.assert_not_called()
    mock_active_container.remove.assert_not_called()


def test_cleanup_dry_run_mode(tmp_path: Path) -> None:
    """Dry-run mode records removals without modifying containers or filesystem."""
    repo = FakeRunRepository()

    # Create stale workspace directory
    stale_ws = tmp_path / "sbx-stale-001"
    stale_ws.mkdir()
    (stale_ws / "build.log").write_text("dummy build data")

    # Set mtime back 48 hours
    past_ts = (datetime.now(UTC) - timedelta(hours=48)).timestamp()
    import os

    os.utime(stale_ws, (past_ts, past_ts))

    mock_container = MagicMock()
    mock_container.id = "c_stale_111111"
    mock_container.labels = {"agency.managed": "true"}

    mock_docker = MagicMock()
    mock_docker.containers.list.return_value = [mock_container]

    service = CleanupService(
        repository=repo,
        docker_client=mock_docker,
        base_workspace_dir=tmp_path,
    )

    summary = service.run_cleanup(retention_hours=24.0, dry_run=True)

    assert summary.dry_run is True
    assert len(summary.containers_removed) == 1
    assert len(summary.workspaces_removed) == 1
    assert summary.bytes_reclaimed > 0

    # Ensure no actual deletion happened
    mock_container.stop.assert_not_called()
    mock_container.remove.assert_not_called()
    assert stale_ws.exists()


def test_cleanup_resilience_to_partial_docker_failures(tmp_path: Path) -> None:
    """If one container removal errors, cleanup continues for remaining containers."""
    repo = FakeRunRepository()

    bad_container = MagicMock()
    bad_container.id = "c_bad_000000"
    bad_container.labels = {"agency.managed": "true"}
    bad_container.stop.side_effect = RuntimeError("Container is deadlocked")

    good_container = MagicMock()
    good_container.id = "c_good_111111"
    good_container.labels = {"agency.managed": "true"}

    mock_docker = MagicMock()
    mock_docker.containers.list.return_value = [bad_container, good_container]

    service = CleanupService(
        repository=repo,
        docker_client=mock_docker,
        base_workspace_dir=tmp_path,
    )

    summary = service.run_cleanup(retention_hours=1.0, dry_run=False)

    assert len(summary.containers_removed) == 2
    assert len(summary.errors) == 1
    assert "deadlocked" in summary.errors[0]
    good_container.stop.assert_called_once()
    good_container.remove.assert_called_once()
