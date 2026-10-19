"""Production Docker-based implementation of SandboxPort."""

import concurrent.futures
import shlex
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

import docker
from docker.errors import APIError, NotFound

from agency.application.ports.sandbox import ExecResult, SandboxPort
from agency.infrastructure.sandbox.errors import (
    CommandTimeoutError,
    ContainerCreationError,
    DockerOperationError,
    InvalidPathError,
    SandboxError,
    SandboxNotFoundError,
)
from agency.infrastructure.sandbox.models import (
    SandboxConfig,
    SandboxContainerInfo,
)
from agency.infrastructure.sandbox.path_policy import PathPolicy


class DockerSandbox(SandboxPort):
    """Production implementation of SandboxPort using isolated Docker containers.

    Features:
    - Opaque sandbox identifier generation.
    - One isolated container per sandbox/run.
    - Strict unprivileged user, capability dropping, and security options.
    - Resource controls: CPU quotas, memory limits, and PID caps.
    - Isolated workspace filesystem mounting with path traversal protection.
    - Bounded execution timeouts and output limits.
    - Idempotent cleanup and destruction.
    """

    def __init__(
        self,
        client: docker.DockerClient | None = None,
        config: SandboxConfig | None = None,
    ) -> None:
        self._config = config or SandboxConfig()
        self._client = client
        self._owns_client = client is None
        self._sandboxes: dict[str, SandboxContainerInfo] = {}

    def _get_client(self) -> docker.DockerClient:
        """Lazily initialize or return the injected Docker client."""
        if self._client is None:
            try:
                self._client = docker.from_env()
            except Exception as exc:
                raise DockerOperationError(
                    "connect",
                    "Could not connect to Docker daemon.",
                    original_error=exc,
                ) from exc
        return self._client

    def create(self, template: str = "default", timeout_seconds: int = 300) -> str:
        """Provision and launch a dedicated, isolated sandbox container."""
        if timeout_seconds <= 0:
            raise SandboxError(
                f"Invalid timeout_seconds '{timeout_seconds}'. Must be > 0."
            )

        client = self._get_client()
        sandbox_id = f"sbx-{uuid.uuid4().hex[:12]}"

        # Allocate host workspace directory
        base_dir = self._config.base_workspace_dir or (
            Path(tempfile.gettempdir()) / "agency_sandboxes"
        )
        host_workspace = base_dir / sandbox_id

        try:
            host_workspace.mkdir(parents=True, exist_ok=True)
            # Ensure unprivileged container user can read/write workspace
            host_workspace.chmod(0o777)
        except Exception as exc:
            raise SandboxError(
                f"Failed to create host workspace directory: {exc}"
            ) from exc

        mounts = {
            str(host_workspace.resolve()): {
                "bind": self._config.container_workspace_dir,
                "mode": "rw",
            }
        }

        labels = {
            "agency.managed": "true",
            "agency.sandbox_id": sandbox_id,
            "agency.template": template,
        }

        container = None
        try:
            container = client.containers.create(
                image=self._config.image,
                command=["sleep", "infinity"],
                volumes=mounts,
                user=self._config.user,
                privileged=False,
                cap_drop=self._config.cap_drop,
                security_opt=self._config.security_opt,
                network_mode=self._config.network_mode,
                nano_cpus=self._config.nano_cpus,
                mem_limit=self._config.mem_limit,
                pids_limit=self._config.pids_limit,
                labels=labels,
                detach=True,
            )
            container.start()
        except Exception as exc:
            # Cleanup on partial creation failure
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            shutil.rmtree(host_workspace, ignore_errors=True)
            raise ContainerCreationError(str(exc), original_error=exc) from exc

        container_id = container.id or ""
        if not container_id:
            raise ContainerCreationError(
                "Container was created without a valid identifier."
            )

        info = SandboxContainerInfo(
            sandbox_id=sandbox_id,
            container_id=container_id,
            host_workspace_path=host_workspace,
            timeout_seconds=timeout_seconds,
        )
        self._sandboxes[sandbox_id] = info
        return sandbox_id

    def exec(
        self,
        sandbox_id: str,
        command: list[str] | str,
        env: dict[str, str] | None = None,
    ) -> ExecResult:
        """Execute a command inside the designated sandbox container."""
        info = self._get_sandbox_info(sandbox_id)
        client = self._get_client()

        # Parse and sanitize command into argument-vector
        if isinstance(command, str):
            clean_cmd = command.strip()
            if not clean_cmd:
                raise SandboxError("Command cannot be empty or whitespace.")
            cmd_args = shlex.split(clean_cmd)
        elif isinstance(command, list):
            if not command:
                raise SandboxError("Command list cannot be empty.")
            cmd_args = [str(arg) for arg in command]
        else:
            raise SandboxError("Command must be a list of strings or a string.")

        try:
            container = client.containers.get(info.container_id)
        except NotFound as exc:
            raise SandboxNotFoundError(sandbox_id) from exc
        except APIError as exc:
            raise DockerOperationError(
                "containers.get", str(exc), original_error=exc
            ) from exc

        timeout = self._config.command_timeout

        def _run_exec() -> Any:
            return container.exec_run(
                cmd=cmd_args,
                stdout=True,
                stderr=True,
                demux=True,
                workdir=self._config.container_workspace_dir,
                environment=env,
                user=self._config.user,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_exec)
            try:
                exec_response = future.result(timeout=timeout)
            except concurrent.futures.TimeoutError as exc:
                raise CommandTimeoutError(
                    command=" ".join(cmd_args),
                    timeout_seconds=float(timeout),
                ) from exc
            except APIError as exc:
                raise DockerOperationError(
                    "exec_run", str(exc), original_error=exc
                ) from exc
            except Exception as exc:
                raise SandboxError(f"Command execution failed: {exc}") from exc

        # Unpack exec result: exit_code and output streams
        if hasattr(exec_response, "exit_code"):
            exit_code: int = int(exec_response.exit_code)
            output_streams: Any = exec_response.output
        else:
            exit_code = int(exec_response[0])
            output_streams = exec_response[1]

        stdout_raw: bytes = b""
        stderr_raw: bytes = b""

        if isinstance(output_streams, tuple):
            stdout_raw = output_streams[0] or b""
            stderr_raw = output_streams[1] or b""
        elif isinstance(output_streams, bytes):
            stdout_raw = output_streams

        stdout_str = stdout_raw.decode("utf-8", errors="replace")
        stderr_str = stderr_raw.decode("utf-8", errors="replace")

        # Enforce output length limit
        max_bytes = self._config.max_output_bytes
        if len(stdout_str) > max_bytes:
            stdout_str = stdout_str[:max_bytes] + "\n[Output truncated]"
        if len(stderr_str) > max_bytes:
            stderr_str = stderr_str[:max_bytes] + "\n[Output truncated]"

        return ExecResult(
            exit_code=exit_code,
            stdout=stdout_str,
            stderr=stderr_str,
        )

    def write_file(self, sandbox_id: str, path: str, content: str | bytes) -> None:
        """Write content to a file inside the isolated sandbox workspace."""
        info = self._get_sandbox_info(sandbox_id)

        payload = content.encode("utf-8") if isinstance(content, str) else content
        PathPolicy.validate_file_size(len(payload), self._config.max_file_size)

        resolved_target = PathPolicy.resolve_safe_path(info.host_workspace_path, path)

        try:
            resolved_target.parent.mkdir(parents=True, exist_ok=True)
            resolved_target.write_bytes(payload)
        except InvalidPathError:
            raise
        except Exception as exc:
            raise SandboxError(f"Failed to write file '{path}': {exc}") from exc

    def read_file(self, sandbox_id: str, path: str) -> str:
        """Read text from a file inside the isolated sandbox workspace."""
        info = self._get_sandbox_info(sandbox_id)

        try:
            resolved_target = PathPolicy.resolve_safe_path(
                info.host_workspace_path, path, must_exist=True
            )
        except FileNotFoundError as exc:
            raise SandboxError(f"File not found in sandbox: '{path}'.") from exc

        if not resolved_target.is_file():
            raise SandboxError(f"Path '{path}' is not a regular file.")

        file_size = resolved_target.stat().st_size
        PathPolicy.validate_file_size(file_size, self._config.max_file_size)

        try:
            return resolved_target.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            raise SandboxError(f"Failed to read file '{path}': {exc}") from exc

    def copy_out(self, sandbox_id: str, src_path: str) -> bytes:
        """Extract bytes of a file from the isolated sandbox workspace."""
        info = self._get_sandbox_info(sandbox_id)

        try:
            resolved_target = PathPolicy.resolve_safe_path(
                info.host_workspace_path, src_path, must_exist=True
            )
        except FileNotFoundError as exc:
            raise SandboxError(f"File not found in sandbox: '{src_path}'.") from exc

        if not resolved_target.is_file():
            raise SandboxError(f"Path '{src_path}' is not a regular file.")

        file_size = resolved_target.stat().st_size
        PathPolicy.validate_file_size(file_size, self._config.max_file_size)

        try:
            return resolved_target.read_bytes()
        except Exception as exc:
            raise SandboxError(f"Failed to copy file '{src_path}': {exc}") from exc

    def destroy(self, sandbox_id: str) -> None:
        """Tear down and destroy the sandbox container and workspace."""
        info = self._sandboxes.get(sandbox_id)
        if info is None:
            raise SandboxNotFoundError(sandbox_id)

        cleanup_error: Exception | None = None

        if not info.is_destroyed:
            client = self._get_client()
            try:
                container = client.containers.get(info.container_id)
                container.remove(force=True)
            except NotFound:
                # Container was already removed externally
                pass
            except Exception as exc:
                cleanup_error = exc

            # Delete host workspace directory
            try:
                shutil.rmtree(info.host_workspace_path, ignore_errors=True)
            except Exception as exc:
                if cleanup_error is None:
                    cleanup_error = exc

            info.is_destroyed = True

        del self._sandboxes[sandbox_id]

        if cleanup_error is not None:
            raise DockerOperationError(
                "destroy",
                f"Failed to clean up sandbox resources: {cleanup_error}",
                original_error=cleanup_error,
            )

    def close(self) -> None:
        """Close Docker client resources if owned."""
        if self._owns_client and self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def _get_sandbox_info(self, sandbox_id: str) -> SandboxContainerInfo:
        """Retrieve container metadata or raise SandboxNotFoundError."""
        info = self._sandboxes.get(sandbox_id)
        if info is None or info.is_destroyed:
            raise SandboxNotFoundError(sandbox_id)
        return info


__all__ = ["DockerSandbox"]
