"""Unit tests for WorkflowRunner shutdown, task draining, and job rejection."""

import asyncio
from unittest.mock import MagicMock

import pytest

from agency.application.services.workflow_runner import WorkflowRunner
from agency.domain.entities.brief import Brief


@pytest.fixture
def mock_workflow_service() -> MagicMock:
    """Provide a mocked WorkflowGraphService."""
    service = MagicMock()
    return service


def sample_brief() -> Brief:
    """Return a valid minimal brief."""
    return Brief(
        client_name="Test Client",
        site_type="Portfolio",
        pages=["home", "about"],
        tone="minimal",
        content_notes="Test brief notes",
    )


def test_workflow_runner_shutdown_cancels_tasks(
    mock_workflow_service: MagicMock,
) -> None:
    """Runner shutdown signals cancellation to active runs and awaits drain."""

    async def _test() -> None:
        runner = WorkflowRunner(workflow_service=mock_workflow_service, sync_mode=False)
        assert runner.is_ready is True
        assert runner.is_shutting_down is False

        brief = sample_brief()

        def slow_work(*args: object, **kwargs: object) -> None:
            import time

            time.sleep(0.5)

        mock_workflow_service.start_workflow.side_effect = slow_work

        runner.submit_run(run_id="run-1", brief=brief, project_id="proj-1")

        # Initiate graceful shutdown
        await runner.shutdown(timeout=1.0)

        assert runner.is_shutting_down is True
        assert runner.is_ready is False
        assert len(runner._active_tasks) == 0

        mock_workflow_service.request_cancellation.assert_called_with(
            run_id="run-1", reason="Application shutdown"
        )

    asyncio.run(_test())


def test_workflow_runner_rejects_new_runs_when_shutting_down(
    mock_workflow_service: MagicMock,
) -> None:
    """When shutting down, submit_run returns False and rejects new submissions."""

    async def _test() -> None:
        runner = WorkflowRunner(workflow_service=mock_workflow_service, sync_mode=True)
        await runner.shutdown()

        assert runner.is_shutting_down is True
        brief = sample_brief()

        result = runner.submit_run(run_id="run-2", brief=brief, project_id="proj-2")
        assert result is False
        mock_workflow_service.start_workflow.assert_not_called()

    asyncio.run(_test())
