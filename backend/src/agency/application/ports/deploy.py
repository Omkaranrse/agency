"""DeployPort definition for web application deployment."""

from abc import ABC, abstractmethod

from agency.domain.entities.deployment import Deployment


class DeployPort(ABC):
    """Abstract port for deploying applications to staging or production."""

    @abstractmethod
    def deploy_staging(
        self,
        project_id: str,
        commit_sha: str,
        artifacts: dict[str, str | bytes] | None = None,
    ) -> Deployment:
        """Deploy a project build to a preview/staging environment.

        Args:
            project_id: Unique project identifier.
            commit_sha: Verified Git commit SHA to deploy.
            artifacts: Optional map of build files to upload.

        Returns:
            A Deployment record containing the preview URL.

        Raises:
            DeployError: If staging deployment fails.
        """

    @abstractmethod
    def deploy_production(
        self,
        project_id: str,
        commit_sha: str,
        artifacts: dict[str, str | bytes] | None = None,
    ) -> Deployment:
        """Promote a project build to the production environment.

        Args:
            project_id: Unique project identifier.
            commit_sha: Verified Git commit SHA to deploy.
            artifacts: Optional map of build files to upload.

        Returns:
            A Deployment record containing preview and production URLs.

        Raises:
            DeployError: If production deployment fails.
        """

    @abstractmethod
    def get_deployment(self, project_id: str) -> Deployment | None:
        """Retrieve the latest active deployment metadata for a project.

        Returns:
            The latest Deployment record, or None if no deployment exists.
        """

    def get_deployment_status(self, project_id: str, deployment_id: str) -> str:
        """Retrieve deployment status string (e.g. 'ready', 'active', 'failed')."""
        return "ready"
