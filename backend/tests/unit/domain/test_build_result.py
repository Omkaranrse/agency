"""Unit tests for BuildResult domain entity."""

import pytest
from pydantic import ValidationError

from agency.domain.entities.build_result import BuildResult


def mutate_attr(obj: object, name: str, value: object) -> None:
    """Helper to attempt dynamic mutation on frozen objects."""
    setattr(obj, name, value)


def test_valid_successful_build_result() -> None:
    """Test valid successful build with commit SHA and workspace path."""
    result = BuildResult(
        workspace_path="/tmp/workspace/agency-app",
        commit_sha="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        build_ok=True,
        logs="Build completed successfully in 4.2s.",
    )
    assert result.build_ok is True
    assert result.commit_sha == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
    assert result.workspace_path == "/tmp/workspace/agency-app"


def test_valid_failed_build_without_commit_sha() -> None:
    """Test valid failed build where commit SHA may not have been created."""
    result = BuildResult(
        workspace_path="/tmp/workspace/agency-app",
        commit_sha=None,
        build_ok=False,
        logs="SyntaxError in index.astro: line 12",
    )
    assert result.build_ok is False
    assert result.commit_sha is None


def test_successful_build_requires_commit_sha() -> None:
    """Test invariant: build_ok=True requires a commit SHA."""
    with pytest.raises(ValidationError) as exc_info:
        BuildResult(
            workspace_path="/tmp/workspace",
            commit_sha=None,
            build_ok=True,
            logs="Everything looks good.",
        )
    assert "must be linked to a valid commit SHA" in str(exc_info.value)


@pytest.mark.parametrize(
    "invalid_sha",
    ["abc", "12345", "not-a-hex-sha-xyz", "g" * 40],
)
def test_invalid_commit_sha_rejected(invalid_sha: str) -> None:
    """Test that invalid commit SHA formats are rejected."""
    with pytest.raises(ValidationError):
        BuildResult(
            workspace_path="/tmp/workspace",
            commit_sha=invalid_sha,
            build_ok=False,
        )


def test_build_result_truncates_oversized_logs() -> None:
    """Test that build logs exceeding policy are safely capped/truncated."""
    oversized_logs = "A" * 150_000
    result = BuildResult(
        workspace_path="/tmp/workspace",
        commit_sha="a1b2c3d",
        build_ok=True,
        logs=oversized_logs,
    )
    assert len(result.logs) <= 100_000
    assert "[... logs truncated by domain policy ...]" in result.logs


def test_build_result_is_immutable() -> None:
    """Test that BuildResult is immutable."""
    result = BuildResult(
        workspace_path="/tmp/workspace",
        commit_sha="a1b2c3d",
        build_ok=True,
        logs="Log",
    )
    with pytest.raises(ValidationError):
        mutate_attr(result, "build_ok", False)
