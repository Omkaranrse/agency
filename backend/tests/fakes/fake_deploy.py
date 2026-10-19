"""In-memory fake implementation of DeployPort for testing."""

from datetime import UTC, datetime
from typing import Any

from pydantic import HttpUrl

from agency.application.ports.deploy import DeployPort
from agency.domain.entities.deployment import Deployment


class FakeDeploy(DeployPort):
    """Deterministic in-memory fake deployment provider."""

    def __init__(self) -> None:
        self._deployments: dict[str, Deployment] = {}
        self._simulated_error: Exception | None = None
        self.calls: list[dict[str, Any]] = []

    def set_failure(self, error: Exception | None) -> None:
        """Configure a simulated deployment infrastructure error."""
        self._simulated_error = error

    def clear(self) -> None:
        """Reset deployments and recorded calls."""
        self._deployments.clear()
        self._simulated_error = None
        self.calls.clear()

    def deploy_staging(self, project_id: str, commit_sha: str) -> Deployment:
        """Generate a deterministic staging deployment with preview URL."""
        if self._simulated_error:
            raise self._simulated_error

        now = datetime.now(UTC)
        url = HttpUrl(f"https://{project_id}-preview.agency.run")
        deployment = Deployment(
            preview_url=url,
            production_url=None,
            provider="fake-cloud",
            deployed_at=now,
        )

        self._deployments[project_id] = deployment
        self.calls.append(
            {
                "op": "deploy_staging",
                "project_id": project_id,
                "commit_sha": commit_sha,
            }
        )
        return deployment

    def deploy_production(self, project_id: str, commit_sha: str) -> Deployment:
        """Generate a deterministic production deployment with public URL."""
        if self._simulated_error:
            raise self._simulated_error

        now = datetime.now(UTC)
        preview_url = HttpUrl(f"https://{project_id}-preview.agency.run")
        prod_url = HttpUrl(f"https://{project_id}.agency.run")
        deployment = Deployment(
            preview_url=preview_url,
            production_url=prod_url,
            provider="fake-cloud",
            deployed_at=now,
        )

        self._deployments[project_id] = deployment
        self.calls.append(
            {
                "op": "deploy_production",
                "project_id": project_id,
                "commit_sha": commit_sha,
            }
        )
        return deployment

    def get_deployment(self, project_id: str) -> Deployment | None:
        """Retrieve latest deployment record for a project."""
        if self._simulated_error:
            raise self._simulated_error
        return self._deployments.get(project_id)
