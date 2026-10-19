"""Unit tests for PathPolicy security and path traversal validations."""

from pathlib import Path

import pytest

from agency.infrastructure.sandbox.errors import (
    FileSizeLimitExceededError,
    InvalidPathError,
)
from agency.infrastructure.sandbox.path_policy import PathPolicy


def test_validate_relative_path_valid_forms() -> None:
    """Test standard valid workspace-relative paths."""
    assert PathPolicy.validate_relative_path("index.ts") == "index.ts"
    assert (
        PathPolicy.validate_relative_path("src/components/Header.tsx")
        == "src/components/Header.tsx"
    )
    assert (
        PathPolicy.validate_relative_path("./nested/dir/file.txt")
        == "nested/dir/file.txt"
    )
    assert PathPolicy.validate_relative_path("a/b/c/d/e.json") == "a/b/c/d/e.json"


@pytest.mark.parametrize(
    "invalid_path",
    [
        "",
        "   ",
        "\t\n",
        "file\x00name.txt",
        "/etc/passwd",
        "/workspace/file.txt",
        "\\Windows\\System32",
        "C:\\autoexec.bat",
        "D:/data.csv",
        "\\\\server\\share\\file.txt",
        "../secret.txt",
        "foo/../../secret.txt",
        "foo/bar/..",
        "..",
        "./../escape",
        "nested/../../../etc/shadow",
    ],
)
def test_validate_relative_path_rejects_unsafe(invalid_path: str) -> None:
    """Test that path traversal, absolute, null-byte, and drive paths are rejected."""
    with pytest.raises(InvalidPathError):
        PathPolicy.validate_relative_path(invalid_path)


def test_resolve_safe_path_success(tmp_path: Path) -> None:
    """Test resolution of valid relative paths within base directory."""
    sub_dir = tmp_path / "src"
    sub_dir.mkdir()
    target_file = sub_dir / "index.js"
    target_file.write_text("console.log(1);")

    resolved = PathPolicy.resolve_safe_path(tmp_path, "src/index.js", must_exist=True)
    assert resolved == target_file.resolve()


def test_resolve_safe_path_nonexistent_must_exist_raises(tmp_path: Path) -> None:
    """Test resolving non-existent path with must_exist=True raises
    FileNotFoundError.
    """
    with pytest.raises(FileNotFoundError):
        PathPolicy.resolve_safe_path(tmp_path, "missing/file.txt", must_exist=True)


def test_resolve_safe_path_target_not_yet_created(tmp_path: Path) -> None:
    """Test resolving a new path to be created within workspace."""
    resolved = PathPolicy.resolve_safe_path(tmp_path, "new_folder/new_file.txt")
    assert resolved.is_relative_to(tmp_path.resolve())


def test_resolve_safe_path_internal_symlink_allowed(tmp_path: Path) -> None:
    """Test that symlinks pointing inside workspace are permitted."""
    real_target = tmp_path / "real_file.txt"
    real_target.write_text("content")

    symlink_file = tmp_path / "link_file.txt"
    symlink_file.symlink_to(real_target)

    resolved = PathPolicy.resolve_safe_path(tmp_path, "link_file.txt", must_exist=True)
    assert resolved == real_target.resolve()


def test_resolve_safe_path_external_symlink_rejected(tmp_path: Path) -> None:
    """Test that symlinks pointing outside workspace are rejected with
    InvalidPathError.
    """
    outside_dir = tmp_path.parent / "outside_dir"
    outside_dir.mkdir(exist_ok=True)
    outside_file = outside_dir / "secret.txt"
    outside_file.write_text("sensitive")

    symlink_file = tmp_path / "symlink_to_outside.txt"
    symlink_file.symlink_to(outside_file)

    with pytest.raises(InvalidPathError, match="points outside workspace root"):
        PathPolicy.resolve_safe_path(tmp_path, "symlink_to_outside.txt")


def test_validate_file_size() -> None:
    """Test file size limit validation."""
    PathPolicy.validate_file_size(size_bytes=100, max_bytes=1000)
    PathPolicy.validate_file_size(size_bytes=1000, max_bytes=1000)

    with pytest.raises(FileSizeLimitExceededError):
        PathPolicy.validate_file_size(size_bytes=1001, max_bytes=1000)
