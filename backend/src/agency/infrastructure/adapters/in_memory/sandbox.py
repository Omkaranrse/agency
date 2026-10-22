"""In-memory sandbox adapter maintaining virtual workspace files."""

import posixpath
import uuid
from typing import Any

from agency.application.errors import (
    SandboxError,
    SandboxNotFoundError,
    SandboxSecurityError,
)
from agency.application.ports.sandbox import ExecResult, SandboxPort


class InMemorySandbox(SandboxPort):
    """Deterministic in-memory virtual sandbox maintaining simulated files."""

    def __init__(self) -> None:
        self._sandboxes: dict[str, dict[str, Any]] = {}
        self._exec_responses: dict[str, ExecResult] = {}
        self._simulated_error: Exception | None = None
        self.calls: list[dict[str, Any]] = []

    def set_failure(self, error: Exception | None) -> None:
        """Configure a simulated sandbox infrastructure failure."""
        self._simulated_error = error

    def set_exec_response(self, command_substr: str, result: ExecResult) -> None:
        """Configure custom execution results for matching command substrings."""
        self._exec_responses[command_substr] = result

    def clear(self) -> None:
        """Reset all sandboxes, responses, and records."""
        self._sandboxes.clear()
        self._exec_responses.clear()
        self._simulated_error = None
        self.calls.clear()

    def _validate_path(self, path: str) -> str:
        """Ensure path is normalized and does not escape workspace sandbox."""
        normalized = posixpath.normpath(path)
        if normalized.startswith("..") or normalized.startswith("/"):
            raise SandboxSecurityError(
                f"Path traversal or absolute path disallowed: '{path}'."
            )
        return normalized

    def create(self, template: str = "default", timeout_seconds: int = 300) -> str:
        """Provision a new in-memory sandbox."""
        if self._simulated_error:
            raise self._simulated_error

        sandbox_id = f"sbx-{uuid.uuid4().hex[:8]}"
        self._sandboxes[sandbox_id] = {
            "template": template,
            "timeout_seconds": timeout_seconds,
            "files": {},
        }
        self.calls.append({"op": "create", "sandbox_id": sandbox_id})
        return sandbox_id

    def exec(
        self,
        sandbox_id: str,
        command: list[str] | str,
        env: dict[str, str] | None = None,
    ) -> ExecResult:
        """Execute a command deterministically within the virtual sandbox."""
        if self._simulated_error:
            raise self._simulated_error
        if sandbox_id not in self._sandboxes:
            raise SandboxNotFoundError(sandbox_id)

        cmd_str = " ".join(command) if isinstance(command, list) else command
        self.calls.append(
            {
                "op": "exec",
                "sandbox_id": sandbox_id,
                "command": cmd_str,
                "env": env,
            }
        )

        for key, res in self._exec_responses.items():
            if key in cmd_str:
                return res

        return ExecResult(exit_code=0, stdout="OK", stderr="")

    def write_file(self, sandbox_id: str, path: str, content: str | bytes) -> None:
        """Write file to virtual sandbox storage."""
        if self._simulated_error:
            raise self._simulated_error
        if sandbox_id not in self._sandboxes:
            raise SandboxNotFoundError(sandbox_id)

        clean_path = self._validate_path(path)
        self._sandboxes[sandbox_id]["files"][clean_path] = content
        self.calls.append(
            {
                "op": "write_file",
                "sandbox_id": sandbox_id,
                "path": clean_path,
            }
        )

    def read_file(self, sandbox_id: str, path: str) -> str:
        """Read text from virtual sandbox storage."""
        if self._simulated_error:
            raise self._simulated_error
        if sandbox_id not in self._sandboxes:
            raise SandboxNotFoundError(sandbox_id)

        clean_path = self._validate_path(path)
        files = self._sandboxes[sandbox_id]["files"]
        if clean_path not in files:
            raise SandboxError(f"File not found in sandbox: '{clean_path}'.")

        data = files[clean_path]
        return data.decode("utf-8") if isinstance(data, bytes) else str(data)

    def copy_out(self, sandbox_id: str, src_path: str) -> bytes:
        """Extract bytes from virtual sandbox storage."""
        if self._simulated_error:
            raise self._simulated_error
        if sandbox_id not in self._sandboxes:
            raise SandboxNotFoundError(sandbox_id)

        clean_path = self._validate_path(src_path)
        files = self._sandboxes[sandbox_id]["files"]
        if clean_path not in files:
            raise SandboxError(f"File not found in sandbox: '{clean_path}'.")

        data = files[clean_path]
        return data if isinstance(data, bytes) else str(data).encode("utf-8")

    def destroy(self, sandbox_id: str) -> None:
        """Tear down virtual sandbox."""
        if self._simulated_error:
            raise self._simulated_error
        if sandbox_id not in self._sandboxes:
            raise SandboxNotFoundError(sandbox_id)

        del self._sandboxes[sandbox_id]
        self.calls.append({"op": "destroy", "sandbox_id": sandbox_id})


# Alias for test backwards-compatibility
FakeSandbox = InMemorySandbox
