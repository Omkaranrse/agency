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


class DeployError(ExternalPortError):
    """Raised when a staging or production deployment operation fails."""
