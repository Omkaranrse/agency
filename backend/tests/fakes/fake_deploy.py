"""In-memory fake implementation of DeployPort for testing."""

import hashlib
from datetime import UTC, datetime
from typing import Any

from pydantic import HttpUrl

from agency.application.errors import (
    DeployAmbiguityError,
    DeployAuthenticationError,
    DeployError,
    DeployRateLimitError,
    DeployTimeoutError,
)
from agency.application.ports.deploy import DeployPort
from agency.domain.entities.deployment import Deployment


class FakeDeploy(DeployPort):
    """Deterministic in-memory fake deployment provider with failure simulation."""

    def __init__(self, provider: str = "fake-cloud") -> None:
        self.provider = provider
        self._deployments: dict[str, Deployment] = {}
        self._projects: set[str] = set()
        self._simulated_error: Exception | None = None
        self.calls: list[dict[str, Any]] = []
        self.simulate_preview_failure: bool = False
        self.simulate_production_failure: bool = False
        self.simulate_rate_limit: float | None = None
        self.simulate_timeout: bool = False
        self.simulate_auth_failure: bool = False
        self.simulate_ambiguous_deploy: bool = False
        self._status_overrides: dict[str, str] = {}

    def set_failure(self, error: Exception | None) -> None:
        """Configure a simulated deployment infrastructure error."""
        self._simulated_error = error

    def clear(self) -> None:
        """Reset deployments and recorded calls."""
        self._deployments.clear()
        self._projects.clear()
        self._simulated_error = None
        self.calls.clear()
        self.simulate_preview_failure = False
        self.simulate_production_failure = False
        self.simulate_rate_limit = None
        self.simulate_timeout = False
        self.simulate_auth_failure = False
        self.simulate_ambiguous_deploy = False
        self._status_overrides.clear()

    def set_deployment_status(self, deployment_id: str, status: str) -> None:
        """Override status returned by get_deployment_status."""
        self._status_overrides[deployment_id] = status

    def _check_simulation_hooks(self, op: str) -> None:
        if self._simulated_error:
            raise self._simulated_error
        if self.simulate_auth_failure:
            raise DeployAuthenticationError(f"Simulated 401 Unauthorized during {op}.")
        if self.simulate_rate_limit is not None:
            raise DeployRateLimitError(
                f"Simulated 429 Rate limit during {op}.",
                retry_after=self.simulate_rate_limit,
            )
        if self.simulate_timeout:
            raise DeployTimeoutError(
                f"Simulated timeout waiting for deployment readiness during {op}."
            )
        if self.simulate_ambiguous_deploy:
            raise DeployAmbiguityError(
                f"Simulated connection reset after {op} dispatch."
            )

    def deploy_staging(
        self,
        project_id: str,
        commit_sha: str,
        artifacts: dict[str, str | bytes] | None = None,
    ) -> Deployment:
        """Generate deterministic staging deployment with preview URL."""
        self._check_simulation_hooks("deploy_staging")
        if self.simulate_preview_failure:
            raise DeployError(
                f"Simulated preview deployment failure for '{project_id}'."
            )

        now = datetime.now(UTC)
        is_reused = project_id in self._projects
        self._projects.add(project_id)

        dep_id = hashlib.sha1(
            f"staging-{project_id}-{commit_sha}".encode()
        ).hexdigest()[:12]
        url = HttpUrl(f"https://{project_id}-preview.agency.run")

        deployment = Deployment(
            preview_url=url,
            production_url=None,
            provider=self.provider,
            deployed_at=now,
            deployment_id=dep_id,
        )

        self._deployments[project_id] = deployment
        self.calls.append(
            {
                "op": "deploy_staging",
                "project_id": project_id,
                "commit_sha": commit_sha,
                "deployment_id": dep_id,
                "artifact_count": len(artifacts) if artifacts else 0,
                "project_reused": is_reused,
            }
        )
        return deployment

    def deploy_production(
        self,
        project_id: str,
        commit_sha: str,
        artifacts: dict[str, str | bytes] | None = None,
    ) -> Deployment:
        """Promote deployment to production with public production URL."""
        self._check_simulation_hooks("deploy_production")
        if self.simulate_production_failure:
            raise DeployError(
                f"Simulated production promotion failure for '{project_id}'."
            )

        now = datetime.now(UTC)
        is_reused = project_id in self._projects
        self._projects.add(project_id)

        dep_id = hashlib.sha1(f"prod-{project_id}-{commit_sha}".encode()).hexdigest()[
            :12
        ]
        preview_url = HttpUrl(f"https://{project_id}-preview.agency.run")
        prod_url = HttpUrl(f"https://{project_id}.agency.run")

        deployment = Deployment(
            preview_url=preview_url,
            production_url=prod_url,
            provider=self.provider,
            deployed_at=now,
            deployment_id=dep_id,
        )

        self._deployments[project_id] = deployment
        self.calls.append(
            {
                "op": "deploy_production",
                "project_id": project_id,
                "commit_sha": commit_sha,
                "deployment_id": dep_id,
                "artifact_count": len(artifacts) if artifacts else 0,
                "project_reused": is_reused,
            }
        )
        return deployment

    def get_deployment(self, project_id: str) -> Deployment | None:
        """Retrieve latest deployment record for a project."""
        self._check_simulation_hooks("get_deployment")
        return self._deployments.get(project_id)

    def get_deployment_status(self, project_id: str, deployment_id: str) -> str:
        """Retrieve deployment status with simulation override support."""
        self._check_simulation_hooks("get_deployment_status")
        return self._status_overrides.get(deployment_id, "success")
