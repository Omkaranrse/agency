"""SandboxPort definition for isolated code execution."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field


class ExecResult(BaseModel):
    """Result of command execution within an isolated sandbox environment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    exit_code: int
    stdout: str = Field(default="")
    stderr: str = Field(default="")

    @property
    def ok(self) -> bool:
        """Return True if command terminated with zero exit code."""
        return self.exit_code == 0


class SandboxPort(ABC):
    """Abstract port for isolated command execution and filesystem isolation.

    Protects the host environment by routing all workspace operations through
    an isolated boundary identified by an opaque sandbox identifier.
    """

    @abstractmethod
    def create(self, template: str = "default", timeout_seconds: int = 300) -> str:
        """Create and start a new isolated sandbox environment.

        Args:
            template: Environment specification (e.g., 'astro-node20').
            timeout_seconds: Maximum wall-clock lifespan for the sandbox.

        Returns:
            An opaque sandbox identifier string.

        Raises:
            SandboxError: If environment provisioning fails.
        """

    @abstractmethod
    def exec(
        self,
        sandbox_id: str,
        command: list[str] | str,
        env: dict[str, str] | None = None,
    ) -> ExecResult:
        """Execute a command within the specified sandbox environment.

        Args:
            sandbox_id: Opaque identifier of the target sandbox.
            command: Command array or string to execute inside the sandbox.
            env: Optional environment variables for the execution context.

        Returns:
            An ExecResult containing exit code, stdout, and stderr.

        Raises:
            SandboxNotFoundError: If the sandbox_id does not exist or has expired.
            SandboxError: If execution could not be dispatched.
        """

    @abstractmethod
    def write_file(self, sandbox_id: str, path: str, content: str | bytes) -> None:
        """Write content to a file inside the isolated sandbox workspace.

        Args:
            sandbox_id: Target sandbox identifier.
            path: Relative path within the sandbox root. Path traversal
                (e.g., '../') must be rejected.
            content: Text or binary payload to write.

        Raises:
            SandboxNotFoundError: If sandbox_id is invalid.
            SandboxSecurityError: If path attempts directory traversal.
            SandboxError: If file creation fails.
        """

    @abstractmethod
    def read_file(self, sandbox_id: str, path: str) -> str:
        """Read text content from a file inside the sandbox workspace.

        Raises:
            SandboxNotFoundError: If sandbox_id is invalid.
            SandboxSecurityError: If path attempts directory traversal.
            SandboxError: If file cannot be read or does not exist.
        """

    @abstractmethod
    def copy_out(self, sandbox_id: str, src_path: str) -> bytes:
        """Extract a file or archive artifact from the sandbox.

        Raises:
            SandboxNotFoundError: If sandbox_id is invalid.
            SandboxSecurityError: If path attempts directory traversal.
            SandboxError: If extraction fails.
        """

    @abstractmethod
    def destroy(self, sandbox_id: str) -> None:
        """Tear down and destroy the sandbox environment.

        Raises:
            SandboxNotFoundError: If sandbox_id is invalid.
        """
