"""Maintenance service for cleaning sandbox containers and workspaces."""

import logging
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from agency.application.ports.run_repository import RunRepositoryPort
from agency.domain.entities.run import Run

logger = logging.getLogger(__name__)


@dataclass
class CleanupSummary:
    """Summary record of maintenance cleanup actions."""

    dry_run: bool
    containers_inspected: int = 0
    containers_removed: list[str] = field(default_factory=list)
    workspaces_inspected: int = 0
    workspaces_removed: list[str] = field(default_factory=list)
    bytes_reclaimed: int = 0
    active_runs_protected: int = 0
    errors: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class CleanupService:
    """Safely identifies and purges stale sandbox containers and temp workspaces.

    Enforces:
    - Protection of active runs in terminal/non-terminal states.
    - Identification of containers strictly via stable ownership labels.
    - Retention-window enforcement.
    - Idempotency and error isolation.
    """

    def __init__(
        self,
        repository: RunRepositoryPort,
        docker_client: Any = None,
        base_workspace_dir: Path | str | None = None,
    ) -> None:
        self.repository = repository
        self.docker_client = docker_client
        self.base_workspace_dir = Path(
            base_workspace_dir or (Path(tempfile.gettempdir()) / "agency_sandboxes")
        )

    def run_cleanup(
        self,
        retention_hours: float = 24.0,
        dry_run: bool = False,
    ) -> CleanupSummary:
        """Execute cleanup routine for orphaned containers and stale workspaces."""
        summary = CleanupSummary(dry_run=dry_run)
        cutoff_time = datetime.now(UTC) - timedelta(hours=retention_hours)

        # 1. Gather all active run IDs to ensure active sandboxes are never purged
        active_run_ids: set[str] = set()
        offset = 0
        limit = 100
        while True:
            runs_slice = self.repository.list(limit=limit, offset=offset)
            if not runs_slice:
                break
            for r in runs_slice:
                if r.state not in Run.TERMINAL_STATES:
                    active_run_ids.add(r.run_id)
            if len(runs_slice) < limit:
                break
            offset += limit

        summary.active_runs_protected = len(active_run_ids)

        # 2. Inspect and cleanup managed containers
        self._cleanup_containers(
            summary=summary,
            active_run_ids=active_run_ids,
            dry_run=dry_run,
        )

        # 3. Inspect and cleanup temporary host workspaces
        self._cleanup_workspaces(
            summary=summary,
            cutoff_time=cutoff_time,
            dry_run=dry_run,
        )

        logger.info(
            "Cleanup complete (dry_run=%s): %d containers, %d dirs, %d bytes reclaimed",
            dry_run,
            len(summary.containers_removed),
            len(summary.workspaces_removed),
            summary.bytes_reclaimed,
        )
        return summary

    def _cleanup_containers(
        self,
        summary: CleanupSummary,
        active_run_ids: set[str],
        dry_run: bool,
    ) -> None:
        """Find and remove abandoned containers labeled agency.managed=true."""
        if self.docker_client is None:
            try:
                import docker

                self.docker_client = docker.from_env()
            except Exception as exc:
                logger.warning(
                    "Docker client unavailable for container cleanup: %s", exc
                )
                summary.errors.append(f"Docker unavailable: {exc}")
                return

        try:
            # Strictly filter by verified ownership label
            containers = self.docker_client.containers.list(
                all=True,
                filters={"label": ["agency.managed=true"]},
            )
        except Exception as exc:
            logger.error("Failed to list Docker containers: %s", exc)
            summary.errors.append(f"Failed to query containers: {exc}")
            return

        for container in containers:
            summary.containers_inspected += 1
            labels = container.labels or {}
            sandbox_id = labels.get("agency.sandbox_id", "")
            run_id = labels.get("agency.run_id", "")

            # If container belongs to a currently active run, protect it
            if run_id and run_id in active_run_ids:
                continue

            summary.containers_removed.append(container.id[:12])
            if not dry_run:
                try:
                    container.stop(timeout=2)
                    container.remove(force=True)
                    logger.info(
                        "Removed abandoned sandbox container %s (%s)",
                        container.id[:12],
                        sandbox_id,
                    )
                except Exception as exc:
                    err_msg = f"Failed removing container {container.id[:12]}: {exc}"
                    logger.warning(err_msg)
                    summary.errors.append(err_msg)

    def _cleanup_workspaces(
        self,
        summary: CleanupSummary,
        cutoff_time: datetime,
        dry_run: bool,
    ) -> None:
        """Find and prune expired sandbox directories in base workspace."""
        if not self.base_workspace_dir.exists():
            return

        for item in self.base_workspace_dir.iterdir():
            if not item.is_dir():
                continue

            # Only inspect sandbox directory patterns
            if not item.name.startswith("sbx-"):
                continue

            summary.workspaces_inspected += 1
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime, tz=UTC)
                if mtime < cutoff_time:
                    size = self._get_dir_size(item)
                    summary.workspaces_removed.append(str(item))
                    summary.bytes_reclaimed += size

                    if not dry_run:
                        shutil.rmtree(item, ignore_errors=True)
                        logger.info(
                            "Pruned expired workspace %s (%d bytes)", item, size
                        )
            except Exception as exc:
                err_msg = f"Failed inspecting workspace {item}: {exc}"
                logger.warning(err_msg)
                summary.errors.append(err_msg)

    @staticmethod
    def _get_dir_size(path: Path) -> int:
        """Compute recursive directory byte size."""
        total = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
        except Exception:
            pass
        return total
