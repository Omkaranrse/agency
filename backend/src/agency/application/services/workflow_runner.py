"""Application-owned workflow execution and background task supervisor."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from agency.application.graph.approval import ApprovalDecision
from agency.application.graph.graph_service import WorkflowGraphService
from agency.domain.entities.brief import Brief

logger = logging.getLogger(__name__)


class WorkflowRunner:
    """Supervised runner coordinating asynchronous LangGraph execution.

    Features:
    - Enforces idempotency key deduplication.
    - Supervised task tracking with deterministic error capture.
    - Graceful cancellation and cleanup during application shutdown.
    """

    def __init__(
        self,
        workflow_service: WorkflowGraphService,
        sync_mode: bool = False,
    ) -> None:
        self.workflow_service = workflow_service
        self.sync_mode = sync_mode
        self._active_tasks: dict[str, asyncio.Task[Any]] = {}
        self._idempotency_keys: dict[str, str] = {}
        self._completed_runs: set[str] = set()
        self._is_shutting_down: bool = False

    @property
    def is_shutting_down(self) -> bool:
        """Return True if runner is draining and rejecting new tasks."""
        return self._is_shutting_down

    @property
    def is_ready(self) -> bool:
        """Return True if runner is operational and accepting new tasks."""
        return not self._is_shutting_down

    def has_idempotency_key(self, key: str) -> bool:
        """Return True if an execution has already been submitted under key."""
        return key in self._idempotency_keys

    def submit_run(
        self,
        run_id: str,
        brief: Brief,
        project_id: str,
        idempotency_key: str | None = None,
    ) -> bool:
        """Submit a new workflow run for asynchronous processing.

        Returns:
            bool: True if execution started, False if deduplicated or shutting down.
        """
        if self._is_shutting_down:
            logger.warning(
                "Run '%s' rejected: WorkflowRunner is shutting down.", run_id
            )
            return False

        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                logger.info(
                    "Duplicate run creation request ignored for key '%s'",
                    idempotency_key,
                )
                return False
            self._idempotency_keys[idempotency_key] = run_id

        def _work() -> None:
            try:
                self.workflow_service.start_workflow(
                    brief=brief,
                    project_id=project_id,
                    run_id=run_id,
                )
            except Exception as exc:
                logger.error(
                    "Workflow run '%s' failed during background execution: %s",
                    run_id,
                    exc,
                    exc_info=True,
                )
            finally:
                self._completed_runs.add(run_id)

        if self.sync_mode:
            _work()
            return True

        self._spawn_tracked_task(run_id, _work)
        return True

    def submit_approval(
        self,
        run_id: str,
        decision: ApprovalDecision,
        idempotency_key: str | None = None,
    ) -> bool:
        """Submit a human approval decision for asynchronous resumption."""
        if idempotency_key:
            if idempotency_key in self._idempotency_keys:
                logger.info(
                    "Duplicate approval request ignored for key '%s'",
                    idempotency_key,
                )
                return False
            self._idempotency_keys[idempotency_key] = run_id

        def _work() -> None:
            try:
                self.workflow_service.submit_approval(run_id, decision)
            except Exception as exc:
                logger.error(
                    "Approval for run '%s' failed in background: %s",
                    run_id,
                    exc,
                    exc_info=True,
                )

        if self.sync_mode:
            _work()
            return True

        self._spawn_tracked_task(run_id, _work)
        return True

    def cancel_run(self, run_id: str, reason: str = "Cancelled by user") -> None:
        """Request cancellation of an active workflow."""
        if task := self._active_tasks.get(run_id):
            task.cancel()

        self.workflow_service.request_cancellation(run_id=run_id, reason=reason)

    def _spawn_tracked_task(self, run_id: str, work: Callable[[], None]) -> None:
        """Spawn a supervised asyncio task running work in a separate thread."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        async def _run_task() -> None:
            try:
                await loop.run_in_executor(None, work)
            except asyncio.CancelledError:
                logger.info("Background task for run '%s' was cancelled.", run_id)
            finally:
                self._active_tasks.pop(run_id, None)

        task = loop.create_task(_run_task())
        self._active_tasks[run_id] = task

    async def shutdown(self, timeout: float = 5.0) -> None:
        """Signal workflow cancellation, drain running tasks, and clean up resources."""
        self._is_shutting_down = True

        # 1. Signal cancellation to all active workflow runs
        for run_id in list(self._active_tasks.keys()):
            try:
                self.workflow_service.request_cancellation(
                    run_id=run_id, reason="Application shutdown"
                )
            except Exception as exc:
                logger.warning(
                    "Error requesting cancellation for run '%s' during shutdown: %s",
                    run_id,
                    exc,
                )

        # 2. Cancel and await background asyncio tasks
        if self._active_tasks:
            tasks = list(self._active_tasks.values())
            for task in tasks:
                task.cancel()

            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except TimeoutError:
                logger.warning(
                    "Workflow runner shutdown timed out after %.1fs", timeout
                )
            finally:
                self._active_tasks.clear()
