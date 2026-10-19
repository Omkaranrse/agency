"""Unit tests for DockerSandbox adapter using mock Docker client."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from docker.errors import APIError, NotFound

from agency.application.ports.sandbox import ExecResult
from agency.infrastructure.sandbox.docker_sandbox import DockerSandbox
from agency.infrastructure.sandbox.errors import (
    CommandTimeoutError,
    ContainerCreationError,
    FileSizeLimitExceededError,
    InvalidPathError,
    SandboxError,
    SandboxNotFoundError,
)
from agency.infrastructure.sandbox.models import SandboxConfig


@pytest.fixture
def mock_docker_client() -> MagicMock:
    """Provide a mock DockerClient instance."""
    client = MagicMock()
    # Mock container
    mock_container = MagicMock()
    mock_container.id = "mock-container-id-12345"
    mock_container.exec_run.return_value = (0, (b"mock stdout", b""))

    client.containers.create.return_value = mock_container
    client.containers.get.return_value = mock_container
    return client


@pytest.fixture
def sandbox_config(tmp_path: Path) -> SandboxConfig:
    """Provide sandbox configuration pointing to tmp_path for workspaces."""
    return SandboxConfig(
        image="agency-sandbox:test",
        base_workspace_dir=tmp_path / "workspaces",
        command_timeout=2,
        max_file_size=1024,
        max_output_bytes=2048,
    )


def test_create_sandbox_parameters(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify container creation options, resource limits, and security flags."""
    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)
    sbx_id = sandbox.create(template="node20-test", timeout_seconds=120)

    assert sbx_id.startswith("sbx-")
    assert mock_docker_client.containers.create.called

    _, kwargs = mock_docker_client.containers.create.call_args
    assert kwargs["image"] == "agency-sandbox:test"
    assert kwargs["command"] == ["sleep", "infinity"]
    assert kwargs["user"] == "1000:1000"
    assert kwargs["privileged"] is False
    assert kwargs["cap_drop"] == ["ALL"]
    assert kwargs["security_opt"] == ["no-new-privileges:true"]
    assert kwargs["network_mode"] == "none"
    assert kwargs["nano_cpus"] == 1_000_000_000
    assert kwargs["mem_limit"] == "512m"
    assert kwargs["pids_limit"] == 100
    assert kwargs["labels"]["agency.sandbox_id"] == sbx_id
    assert kwargs["labels"]["agency.template"] == "node20-test"

    # Verify workspace directory exists on host
    assert sandbox_config.base_workspace_dir is not None
    expected_dir = sandbox_config.base_workspace_dir / sbx_id
    assert expected_dir.exists()


def test_create_sandbox_cleans_up_on_failure(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify that failed container creation cleans up host workspace."""
    mock_docker_client.containers.create.side_effect = APIError("Engine out of memory")
    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)

    with pytest.raises(ContainerCreationError):
        sandbox.create()

    # Workspace directory must have been cleaned up
    base = sandbox_config.base_workspace_dir
    assert base is not None
    if base.exists():
        assert len(list(base.iterdir())) == 0


def test_exec_command_success(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify command execution returns typed ExecResult."""
    mock_container = mock_docker_client.containers.get.return_value
    mock_container.exec_run.return_value = (0, (b"hello world\n", b""))

    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)
    sbx_id = sandbox.create()

    result = sandbox.exec(sbx_id, ["echo", "hello", "world"])

    assert isinstance(result, ExecResult)
    assert result.exit_code == 0
    assert result.stdout == "hello world\n"
    assert result.stderr == ""
    assert result.ok is True


def test_exec_command_string_parsing(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify string commands are safely split with shlex."""
    mock_container = mock_docker_client.containers.get.return_value
    mock_container.exec_run.return_value = (0, (b"ok", b""))

    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)
    sbx_id = sandbox.create()

    sandbox.exec(sbx_id, "git commit -m 'initial prototype'")

    _, kwargs = mock_container.exec_run.call_args
    assert kwargs["cmd"] == ["git", "commit", "-m", "initial prototype"]


def test_exec_nonzero_exit_code_is_not_exception(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify nonzero exit codes are returned as results, not infrastructure errors."""
    mock_container = mock_docker_client.containers.get.return_value
    mock_container.exec_run.return_value = (1, (b"", b"Test failed"))

    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)
    sbx_id = sandbox.create()

    result = sandbox.exec(sbx_id, ["pnpm", "test"])
    assert result.exit_code == 1
    assert result.stderr == "Test failed"
    assert result.ok is False


def test_exec_command_empty_rejected(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify empty or whitespace command is rejected."""
    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)
    sbx_id = sandbox.create()

    with pytest.raises(SandboxError, match="cannot be empty"):
        sandbox.exec(sbx_id, "")

    with pytest.raises(SandboxError, match="cannot be empty"):
        sandbox.exec(sbx_id, [])


def test_exec_command_timeout(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify command execution timeout triggers CommandTimeoutError."""
    import time

    def slow_exec(*args: object, **kwargs: object) -> tuple[int, tuple[bytes, bytes]]:
        time.sleep(3)
        return (0, (b"", b""))

    mock_container = mock_docker_client.containers.get.return_value
    mock_container.exec_run.side_effect = slow_exec

    short_timeout_config = SandboxConfig(
        command_timeout=1,
        base_workspace_dir=sandbox_config.base_workspace_dir,
    )
    sandbox = DockerSandbox(client=mock_docker_client, config=short_timeout_config)
    sbx_id = sandbox.create()

    with pytest.raises(CommandTimeoutError):
        sandbox.exec(sbx_id, ["sleep", "10"])


def test_exec_output_truncation(
    mock_docker_client: MagicMock,
    tmp_path: Path,
) -> None:
    """Verify outputs larger than max_output_bytes are safely truncated."""
    small_output_config = SandboxConfig(
        max_output_bytes=20,
        base_workspace_dir=tmp_path / "workspaces",
    )
    mock_container = mock_docker_client.containers.get.return_value
    mock_container.exec_run.return_value = (
        0,
        (b"A" * 100, b"B" * 100),
    )

    sandbox = DockerSandbox(client=mock_docker_client, config=small_output_config)
    sbx_id = sandbox.create()

    result = sandbox.exec(sbx_id, "cat large.log")
    assert len(result.stdout) < 50
    assert "[Output truncated]" in result.stdout
    assert "[Output truncated]" in result.stderr


def test_file_operations_happy_path(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify write_file, read_file, and copy_out operations."""
    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)
    sbx_id = sandbox.create()

    # Write text
    sandbox.write_file(sbx_id, "src/main.ts", "console.log('test');")

    # Read text
    content = sandbox.read_file(sbx_id, "src/main.ts")
    assert content == "console.log('test');"

    # Copy out bytes
    raw = sandbox.copy_out(sbx_id, "src/main.ts")
    assert raw == b"console.log('test');"


def test_file_operations_reject_traversal(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify directory traversal is blocked across write, read, and copy_out."""
    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)
    sbx_id = sandbox.create()

    with pytest.raises(InvalidPathError):
        sandbox.write_file(sbx_id, "../escape.txt", "data")

    with pytest.raises(InvalidPathError):
        sandbox.read_file(sbx_id, "/etc/passwd")

    with pytest.raises(InvalidPathError):
        sandbox.copy_out(sbx_id, "nested/../../outside.txt")


def test_file_size_limit_exceeded(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify payloads exceeding max_file_size raise FileSizeLimitExceededError."""
    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)
    sbx_id = sandbox.create()

    large_payload = "x" * (sandbox_config.max_file_size + 1)
    with pytest.raises(FileSizeLimitExceededError):
        sandbox.write_file(sbx_id, "large.txt", large_payload)


def test_destroy_sandbox_lifecycle(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify destroy removes container and deletes host workspace."""
    mock_container = mock_docker_client.containers.get.return_value

    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)
    sbx_id = sandbox.create()

    workspace_dir = sandbox_config.base_workspace_dir / sbx_id  # type: ignore[operator]
    assert workspace_dir.exists()

    sandbox.destroy(sbx_id)

    mock_container.remove.assert_called_with(force=True)
    assert not workspace_dir.exists()

    # Second destroy call must raise SandboxNotFoundError
    # (idempotent / already destroyed)
    with pytest.raises(SandboxNotFoundError):
        sandbox.destroy(sbx_id)


def test_destroy_handles_already_removed_container(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify destroy succeeds even if container was already removed in Docker."""
    mock_docker_client.containers.get.side_effect = NotFound("Container not found")

    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)
    sbx_id = sandbox.create()

    # Should not raise exception when container is NotFound
    sandbox.destroy(sbx_id)


def test_unknown_sandbox_id_raises_not_found(
    mock_docker_client: MagicMock,
    sandbox_config: SandboxConfig,
) -> None:
    """Verify unknown sandbox_id raises SandboxNotFoundError for all operations."""
    sandbox = DockerSandbox(client=mock_docker_client, config=sandbox_config)

    with pytest.raises(SandboxNotFoundError):
        sandbox.exec("sbx-unknown", "ls")

    with pytest.raises(SandboxNotFoundError):
        sandbox.write_file("sbx-unknown", "test.txt", "content")

    with pytest.raises(SandboxNotFoundError):
        sandbox.read_file("sbx-unknown", "test.txt")

    with pytest.raises(SandboxNotFoundError):
        sandbox.copy_out("sbx-unknown", "test.txt")

    with pytest.raises(SandboxNotFoundError):
        sandbox.destroy("sbx-unknown")
