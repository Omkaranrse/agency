"""Application-level exceptions for Agency."""


class ApplicationError(Exception):
    """Base class for all application layer errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RunNotFoundError(ApplicationError):
    """Raised when a requested run does not exist in the repository."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"Run '{run_id}' was not found.")


class InvalidRequestError(ApplicationError):
    """Raised when an application use case request is invalid."""


class RevisionLimitExceededError(ApplicationError):
    """Raised when a revision request exceeds the maximum allowed limit."""

    def __init__(self, run_id: str, max_revisions: int) -> None:
        self.run_id = run_id
        self.max_revisions = max_revisions
        super().__init__(
            f"Run '{run_id}' has reached the maximum permitted revisions "
            f"({max_revisions})."
        )


class ExternalPortError(ApplicationError):
    """Base exception for external port operations that fail."""


class RepositoryError(ExternalPortError):
    """Raised when a persistence operation fails in the repository port."""


class EventPublicationError(ExternalPortError):
    """Raised when event publishing fails after aggregate state has been changed."""


class LLMError(ExternalPortError):
    """Raised when an LLM provider fails to generate or validate a response."""


class SandboxError(ExternalPortError):
    """Base exception for sandbox execution and lifecycle operations."""


class SandboxNotFoundError(SandboxError):
    """Raised when the specified sandbox ID does not exist."""

    def __init__(self, sandbox_id: str) -> None:
        self.sandbox_id = sandbox_id
        super().__init__(f"Sandbox '{sandbox_id}' not found.")


class SandboxSecurityError(SandboxError):
    """Raised when an unsafe path or disallowed operation is attempted in sandbox."""


class GitError(ExternalPortError):
    """Raised when a version control operation fails in the Git port."""


class GitAuthenticationError(GitError):
    """Raised when VCS authentication or permission fails."""


class GitConflictError(GitError):
    """Raised when a repository, branch, or commit conflict occurs."""


class GitRateLimitError(GitError):
    """Raised when GitHub rate limit is exceeded."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class GitValidationError(GitError):
    """Raised when unsafe files, secret leaks, or invalid repo names are detected."""


class GitAmbiguityError(GitError):
    """Raised when network drops make the remote Git operation status indeterminate."""


class DeployError(ExternalPortError):
    """Raised when a staging or production deployment operation fails."""


class DeployAuthenticationError(DeployError):
    """Raised when deployment provider authentication or authorization fails."""


class DeployRateLimitError(DeployError):
    """Raised when Cloudflare API rate limits are hit."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class DeployTimeoutError(DeployError):
    """Raised when deployment readiness polling exceeds bounded timeout."""


class DeploySmokeTestError(DeployError):
    """Raised when smoke tests against preview or production deployment fail."""


class DeployAmbiguityError(DeployError):
    """Raised when connection drops make remote deployment state ambiguous."""


class DeployValidationError(DeployError):
    """Raised when deployment project name or payload fails validation."""


class ArtifactError(ApplicationError):
    """Base exception for artifact operations."""


class ArtifactNotFoundError(ArtifactError):
    """Raised when an artifact cannot be located for a given run."""

    def __init__(self, run_id: str, artifact_id: str) -> None:
        self.run_id = run_id
        self.artifact_id = artifact_id
        super().__init__(f"Artifact '{artifact_id}' was not found for run '{run_id}'.")


class ArtifactAccessDeniedError(ArtifactError):
    """Raised when artifact access is denied due to traversal or security rules."""
