"""Path validation and containment policies for sandbox operations."""

import os
from pathlib import Path

from agency.infrastructure.sandbox.errors import (
    FileSizeLimitExceededError,
    InvalidPathError,
)


class PathPolicy:
    """Enforces strict path containment within a designated sandbox workspace."""

    @staticmethod
    def validate_relative_path(path: str) -> str:
        """Validate that a path string is relative, normalized, and safe.

        Rejects:
        - Empty or whitespace paths
        - Null bytes
        - Absolute paths (POSIX and Windows drive/UNC roots)
        - Paths containing parent traversal '..'

        Returns:
            A normalized POSIX relative path string.
        """
        if not path or not path.strip():
            raise InvalidPathError(path, "Path cannot be empty or whitespace.")

        clean = path.strip()

        if "\x00" in clean:
            raise InvalidPathError(path, "Null bytes are not allowed in paths.")

        # Check for leading slashes or Windows drives/UNC
        if clean.startswith("/") or clean.startswith("\\"):
            raise InvalidPathError(path, "Absolute paths are strictly disallowed.")

        if ":" in clean and (clean[1:2] == ":" or clean.startswith("\\\\")):
            raise InvalidPathError(
                path, "Drive letters and UNC paths are strictly disallowed."
            )

        # Check for traversal components before normalization
        raw_parts = Path(clean).parts
        if ".." in raw_parts or any(".." in part for part in raw_parts):
            raise InvalidPathError(path, "Directory traversal ('..') is disallowed.")

        # Normalize path
        norm = os.path.normpath(clean)
        if norm.startswith("..") or "/../" in norm or norm.endswith("/.."):
            raise InvalidPathError(path, "Directory traversal ('..') is disallowed.")

        parts = Path(norm).parts
        if ".." in parts:
            raise InvalidPathError(path, "Directory traversal ('..') is disallowed.")

        return norm.replace("\\", "/")

    @classmethod
    def resolve_safe_path(
        cls,
        base_dir: Path,
        relative_path: str,
        must_exist: bool = False,
    ) -> Path:
        """Resolve a relative path against base_dir and verify strict containment.

        Ensures:
        - Relative path validation passes.
        - Canonical base directory exists.
        - Resolved path lies strictly inside canonical base directory.
        - No symlink along the path escapes the workspace root.

        Returns:
            The resolved, validated Path object.
        """
        clean_rel = cls.validate_relative_path(relative_path)

        canonical_base = base_dir.resolve(strict=True)

        # Check each component of the path to prevent symlink escapes
        current = canonical_base
        for part in Path(clean_rel).parts:
            current = current / part
            if current.is_symlink():
                resolved_link = current.resolve()
                if not resolved_link.is_relative_to(canonical_base):
                    raise InvalidPathError(
                        relative_path,
                        f"Symlink '{part}' points outside workspace root.",
                    )

        resolved_target = current.resolve(strict=must_exist)
        if not resolved_target.is_relative_to(canonical_base):
            raise InvalidPathError(
                relative_path,
                f"Resolved path '{resolved_target}' escapes workspace root.",
            )

        return resolved_target

    @staticmethod
    def validate_file_size(size_bytes: int, max_bytes: int) -> None:
        """Verify that a payload or file size does not exceed the allowed threshold."""
        if size_bytes > max_bytes:
            raise FileSizeLimitExceededError(
                limit_bytes=max_bytes, observed_bytes=size_bytes
            )


__all__ = ["PathPolicy"]
