"""Netlify cloud deployment adapter implementing DeployPort."""

import os
from datetime import UTC, datetime
from typing import Any

import requests
from pydantic import HttpUrl

from agency.application.errors import (
    DeployAuthenticationError,
    DeployError,
    DeployRateLimitError,
    DeployTimeoutError,
)
from agency.application.ports.deploy import DeployPort
from agency.domain.entities.deployment import Deployment
from agency.infrastructure.adapters.in_memory.deploy import InMemoryDeploy


class NetlifyDeploymentAdapter(DeployPort):
    """Cloud deployment adapter targeting Netlify REST API with fallback."""

    def __init__(
        self,
        auth_token: str | None = None,
        site_id: str | None = None,
        http_client: Any | None = None,
        fallback_adapter: DeployPort | None = None,
    ) -> None:
        env_token = os.environ.get("NETLIFY_AUTH_TOKEN", "").strip()
        env_site = os.environ.get("NETLIFY_SITE_ID", "").strip()
        self.auth_token = auth_token or (env_token if env_token else None)
        self.site_id = site_id or (env_site if env_site else None)
        self.http_client = http_client or requests.Session()
        self.fallback = fallback_adapter or InMemoryDeploy(provider="local-preview")
        self._deployments: dict[str, Deployment] = {}

    def deploy_staging(
        self,
        project_id: str,
        commit_sha: str,
        artifacts: dict[str, str | bytes] | None = None,
    ) -> Deployment:
        """Deploy build artifacts to a staging/preview environment."""
        if not self.auth_token:
            return self.fallback.deploy_staging(project_id, commit_sha, artifacts)

        short_sha = commit_sha[:7] if commit_sha else "staging"
        site = self.site_id or project_id

        try:
            resp = self.http_client.post(
                f"https://api.netlify.com/api/v1/sites/{site}/deploys",
                json={
                    "title": f"Preview deploy for commit {short_sha}",
                    "draft": True,
                },
                headers={
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        except requests.exceptions.Timeout as exc:
            raise DeployTimeoutError(f"Deployment request timed out: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise DeployError(
                f"Network error during staging deployment: {exc}"
            ) from exc

        if resp.status_code in (401, 403):
            raise DeployAuthenticationError("Invalid or unauthorized Netlify token.")
        if resp.status_code == 429:
            retry_after: float | None = None
            if "Retry-After" in resp.headers:
                try:
                    retry_after = float(resp.headers["Retry-After"])
                except ValueError:
                    pass
            raise DeployRateLimitError(
                "Netlify API rate limit exceeded.", retry_after=retry_after
            )
        if resp.status_code >= 500:
            raise DeployError(f"Netlify server error: HTTP {resp.status_code}")
        if not resp.ok:
            raise DeployError(
                f"Netlify deployment failed with status {resp.status_code}"
            )

        preview_url = HttpUrl(f"https://deploy-preview-{short_sha}--{site}.netlify.app")
        deployment = Deployment(
            preview_url=preview_url,
            provider="netlify",
            deployed_at=datetime.now(UTC),
            deployment_id=f"deploy-{short_sha}",
        )
        self._deployments[project_id] = deployment
        return deployment

    def deploy_production(
        self,
        project_id: str,
        commit_sha: str,
        artifacts: dict[str, str | bytes] | None = None,
    ) -> Deployment:
        """Promote a verified build to production on Netlify."""
        if not self.auth_token:
            return self.fallback.deploy_production(project_id, commit_sha, artifacts)

        short_sha = commit_sha[:7] if commit_sha else "prod"
        site = self.site_id or project_id

        try:
            resp = self.http_client.post(
                f"https://api.netlify.com/api/v1/sites/{site}/deploys",
                json={
                    "title": f"Production release for commit {short_sha}",
                    "draft": False,
                },
                headers={
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        except requests.exceptions.Timeout as exc:
            raise DeployTimeoutError(f"Production deploy timed out: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise DeployError(f"Network error during production deploy: {exc}") from exc

        if resp.status_code in (401, 403):
            raise DeployAuthenticationError("Invalid or unauthorized Netlify token.")
        if resp.status_code == 429:
            retry_after = None
            if "Retry-After" in resp.headers:
                try:
                    retry_after = float(resp.headers["Retry-After"])
                except ValueError:
                    pass
            raise DeployRateLimitError(
                "Netlify rate limit exceeded.", retry_after=retry_after
            )
        if resp.status_code >= 500:
            raise DeployError(f"Netlify server error HTTP {resp.status_code}")
        if not resp.ok:
            raise DeployError(f"Production deployment failed: HTTP {resp.status_code}")

        preview_url = HttpUrl(f"https://deploy-preview-{short_sha}--{site}.netlify.app")
        production_url = HttpUrl(f"https://{site}.netlify.app")
        deployment = Deployment(
            preview_url=preview_url,
            production_url=production_url,
            provider="netlify",
            deployed_at=datetime.now(UTC),
            deployment_id=f"prod-{short_sha}",
        )
        self._deployments[project_id] = deployment
        return deployment

    def get_deployment(self, project_id: str) -> Deployment | None:
        """Retrieve the latest deployment metadata for a project."""
        if project_id in self._deployments:
            return self._deployments[project_id]
        return self.fallback.get_deployment(project_id)
