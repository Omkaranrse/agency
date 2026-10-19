"""Typed sandbox infrastructure exceptions."""

from agency.application.errors import (
    SandboxError,
    SandboxNotFoundError,
    SandboxSecurityError,
)


class SandboxAlreadyExistsError(SandboxError):
    """Raised when attempting to create a sandbox with an ID that already exists."""

    def __init__(self, sandbox_id: str) -> None:
        self.sandbox_id = sandbox_id
        super().__init__(f"Sandbox '{sandbox_id}' already exists.")


class InvalidPathError(SandboxSecurityError):
    """Raised when a path violates traversal or security policy."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid path '{path}': {reason}")


class CommandTimeoutError(SandboxError):
    """Raised when command execution exceeds the configured timeout limit."""

    def __init__(self, command: str, timeout_seconds: float) -> None:
        self.command = command
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Command execution timed out after {timeout_seconds} seconds."
        )


class OutputLimitExceededError(SandboxError):
    """Raised when captured command output exceeds maximum allowed bytes."""

    def __init__(self, limit_bytes: int, observed_bytes: int) -> None:
        self.limit_bytes = limit_bytes
        self.observed_bytes = observed_bytes
        super().__init__(
            f"Output limit exceeded: {observed_bytes} bytes (max: {limit_bytes} bytes)."
        )


class FileSizeLimitExceededError(SandboxError):
    """Raised when a file read or write exceeds maximum permitted size."""

    def __init__(self, limit_bytes: int, observed_bytes: int) -> None:
        self.limit_bytes = limit_bytes
        self.observed_bytes = observed_bytes
        super().__init__(
            f"File size limit exceeded: {observed_bytes} bytes "
            f"(max: {limit_bytes} bytes)."
        )


class ContainerCreationError(SandboxError):
    """Raised when container provisioning fails in Docker."""

    def __init__(self, reason: str, original_error: Exception | None = None) -> None:
        self.original_error = original_error
        super().__init__(f"Failed to create sandbox container: {reason}")


class DockerOperationError(SandboxError):
    """Raised when a Docker API operation fails."""

    def __init__(
        self,
        operation: str,
        reason: str,
        original_error: Exception | None = None,
    ) -> None:
        self.operation = operation
        self.original_error = original_error
        super().__init__(f"Docker operation '{operation}' failed: {reason}")


class SandboxResourceError(SandboxError):
    """Raised when a sandbox runs out of resources or hits system exhaustion."""


__all__ = [
    "CommandTimeoutError",
    "ContainerCreationError",
    "DockerOperationError",
    "FileSizeLimitExceededError",
    "InvalidPathError",
    "OutputLimitExceededError",
    "SandboxAlreadyExistsError",
    "SandboxError",
    "SandboxNotFoundError",
    "SandboxResourceError",
    "SandboxSecurityError",
]
