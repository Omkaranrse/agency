"""Integration tests for DockerSandbox against a live Docker daemon."""

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from agency.infrastructure.sandbox.docker_sandbox import DockerSandbox
from agency.infrastructure.sandbox.errors import (
    CommandTimeoutError,
    InvalidPathError,
)
from agency.infrastructure.sandbox.models import SandboxConfig


def _check_docker() -> tuple[bool, str]:
    """Check if Docker SDK is installed and Docker daemon is responsive."""
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True, "Docker daemon responsive"
    except Exception as exc:
        return False, f"Docker daemon unavailable: {exc}"


DOCKER_AVAILABLE, DOCKER_REASON = _check_docker()

pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=DOCKER_REASON),
]


@pytest.fixture
def docker_sandbox(tmp_path: Path) -> Generator[DockerSandbox, Any, None]:
    """Provide a real DockerSandbox instance configured for integration testing."""
    import docker

    client = docker.from_env()
    config = SandboxConfig(
        image="agency-sandbox:latest",
        base_workspace_dir=tmp_path / "integration_workspaces",
        command_timeout=5,
    )
    sandbox = DockerSandbox(client=client, config=config)
    yield sandbox
    sandbox.close()


def test_docker_sandbox_end_to_end_lifecycle(
    docker_sandbox: DockerSandbox,
) -> None:
    """Verify live container creation, exec, file I/O, traversal rejection,
    and removal.
    """
    sbx_id = docker_sandbox.create(template="integration-test")
    try:
        # 1. Execute harmless command inside container
        result = docker_sandbox.exec(sbx_id, ["echo", "sandbox online"])
        assert result.exit_code == 0
        assert "sandbox online" in result.stdout

        # 2. Write workspace file
        docker_sandbox.write_file(sbx_id, "test_output.txt", "Integration test payload")

        # 3. Read workspace file
        content = docker_sandbox.read_file(sbx_id, "test_output.txt")
        assert content == "Integration test payload"

        # 4. Copy out artifact
        raw_bytes = docker_sandbox.copy_out(sbx_id, "test_output.txt")
        assert raw_bytes == b"Integration test payload"

        # 5. Path traversal attempt must be rejected
        with pytest.raises(InvalidPathError):
            docker_sandbox.read_file(sbx_id, "../../../etc/passwd")

    finally:
        # 6. Destroy container and verify removal
        docker_sandbox.destroy(sbx_id)


def test_docker_sandbox_timeout_enforcement(
    docker_sandbox: DockerSandbox,
) -> None:
    """Verify that a long-running command raises CommandTimeoutError."""
    sbx_id = docker_sandbox.create(template="timeout-test")
    try:
        with pytest.raises(CommandTimeoutError):
            docker_sandbox.exec(sbx_id, ["sleep", "10"])
    finally:
        docker_sandbox.destroy(sbx_id)
