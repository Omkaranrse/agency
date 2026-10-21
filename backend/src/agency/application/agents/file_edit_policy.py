"""Deterministic file edit security and validation policy for Builder proposals."""

import json
import re
from pathlib import PurePosixPath

from agency.application.agents.models import (
    BuilderContext,
    BuilderRawEdit,
    EditCategory,
    FileEditProposal,
)
from agency.application.errors import ApplicationError

DEFAULT_ALLOWED_CONTENT_PATHS = frozenset(
    {
        "src/content/site.json",
        "src/content/home.json",
        "src/content/about.json",
        "src/content/projects.json",
        "src/content/contact.json",
        "src/styles/tokens.css",
    }
)

DEFAULT_ALLOWED_COMPONENT_PATHS = frozenset(
    {
        "src/components/Header.astro",
        "src/components/Footer.astro",
        "src/components/Hero.astro",
        "src/components/Card.astro",
        "src/components/Button.astro",
        "src/components/SectionContainer.astro",
    }
)

MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB limit per file
MAX_EDITS_PER_RESPONSE = 10


class FileEditPolicyError(ApplicationError):
    """Base error for file edit policy violations."""


class ForbiddenFileEditError(FileEditPolicyError):
    """Raised when an edit targets a disallowed or unauthorized path."""


class InvalidFileContentError(FileEditPolicyError):
    """Raised when proposed file content fails schema or syntax validation."""


class EditLimitExceededError(FileEditPolicyError):
    """Raised when proposed edits exceed count or size boundaries."""


class FileEditPolicy:
    """Enforces server-side security, path traversal checks, and schema validation."""

    def __init__(
        self,
        allowed_paths: frozenset[str] = DEFAULT_ALLOWED_CONTENT_PATHS,
        allowed_components: frozenset[str] = DEFAULT_ALLOWED_COMPONENT_PATHS,
        max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
        max_edits: int = MAX_EDITS_PER_RESPONSE,
    ) -> None:
        self.allowed_paths = allowed_paths
        self.allowed_components = allowed_components
        self.max_file_size_bytes = max_file_size_bytes
        self.max_edits = max_edits

    def validate_edits(
        self,
        raw_edits: list[BuilderRawEdit],
        context: BuilderContext,
        prompt_version: str = "v1",
    ) -> list[FileEditProposal]:
        """Validate edit proposals against security and schema rules."""
        if len(raw_edits) > self.max_edits:
            raise EditLimitExceededError(
                f"Proposed {len(raw_edits)} edits, exceeding limit of {self.max_edits}."
            )

        seen_paths: set[str] = set()
        validated_proposals: list[FileEditProposal] = []

        for edit in raw_edits:
            normalized_path = self._validate_and_normalize_path(edit.path)

            if normalized_path in seen_paths:
                raise ForbiddenFileEditError(
                    f"Duplicate edit path in proposal batch: '{normalized_path}'."
                )
            seen_paths.add(normalized_path)

            # File size and binary data check
            content_bytes = edit.content.encode("utf-8")
            if len(content_bytes) > self.max_file_size_bytes:
                raise EditLimitExceededError(
                    f"File '{normalized_path}' size ({len(content_bytes)} bytes) "
                    f"exceeds limit of {self.max_file_size_bytes} bytes."
                )
            if b"\x00" in content_bytes:
                raise InvalidFileContentError(
                    f"Binary content or null bytes detected in '{normalized_path}'."
                )

            # Authorization & Category Resolution
            category = self._resolve_and_authorize_category(
                path=normalized_path,
                context=context,
                qa_issue=edit.qa_issue_addressed,
            )

            # Content schema validation
            self._validate_content_syntax_and_schema(normalized_path, edit.content)

            validated_proposals.append(
                FileEditProposal(
                    path=normalized_path,
                    content=edit.content,
                    reason=edit.reason.strip() or "Template customization",
                    qa_issue_addressed=edit.qa_issue_addressed,
                    category=category,
                    prompt_version=prompt_version,
                )
            )

        return validated_proposals

    def _validate_and_normalize_path(self, raw_path: str) -> str:
        """Validate path form against absolute, traversal, and whitespace escapes."""
        stripped = raw_path.strip()
        if not stripped:
            raise ForbiddenFileEditError("File path cannot be empty or whitespace.")

        if "\x00" in stripped:
            raise ForbiddenFileEditError("Null bytes in file path.")

        # Reject backslashes and encoded traversal
        if "\\" in stripped or "%2e" in stripped.lower():
            raise ForbiddenFileEditError(
                f"Invalid or escaped path separators in '{raw_path}'."
            )

        # Reject absolute paths (POSIX and Windows drive letters)
        if stripped.startswith("/") or re.match(r"^[a-zA-Z]:", stripped):
            raise ForbiddenFileEditError(
                f"Absolute file path '{raw_path}' is prohibited."
            )

        posix = PurePosixPath(stripped)
        parts = posix.parts

        if ".." in parts:
            raise ForbiddenFileEditError(
                f"Path traversal ('..') detected in '{raw_path}'."
            )

        normalized = posix.as_posix()
        return normalized

    def _resolve_and_authorize_category(
        self,
        path: str,
        context: BuilderContext,
        qa_issue: str | None,
    ) -> EditCategory:
        """Determine edit category and verify escalation permission."""
        if path == "src/styles/tokens.css":
            return EditCategory.TOKENS

        if path in self.allowed_paths:
            return EditCategory.CONTENT

        if path in self.allowed_components:
            # Component escalation checks
            if not context.allow_component_escalation:
                raise ForbiddenFileEditError(
                    f"Component edit to '{path}' is prohibited without "
                    "explicit escalation authorization."
                )

            # Escalation requires an actual QA failure defect
            has_qa_failures = bool(
                context.qa_report and not context.qa_report.overall_passed
            )
            if not has_qa_failures:
                raise ForbiddenFileEditError(
                    f"Component escalation to '{path}' is not justified "
                    "because all QA checks passed."
                )

            return EditCategory.COMPONENT_ESCALATION

        raise ForbiddenFileEditError(
            f"File path '{path}' is not in the allowed modification list."
        )

    def _validate_content_syntax_and_schema(self, path: str, content: str) -> None:
        """Validate syntax and essential schema invariants for JSON and CSS targets."""
        if path.endswith(".json"):
            try:
                data = json.loads(content)
            except json.JSONDecodeError as exc:
                raise InvalidFileContentError(
                    f"Invalid JSON syntax in '{path}': {exc}"
                ) from exc

            if not isinstance(data, dict):
                raise InvalidFileContentError(
                    f"JSON root in '{path}' must be an object."
                )

            # Specific JSON schema checks matching Astro template
            if path == "src/content/site.json":
                for required_key in ("clientName", "siteTitle", "nav"):
                    if required_key not in data:
                        raise InvalidFileContentError(
                            f"Missing required field '{required_key}' in site.json."
                        )
            elif path == "src/content/home.json":
                for required_key in ("heroEyebrow", "headline", "supportingCopy"):
                    if required_key not in data:
                        raise InvalidFileContentError(
                            f"Missing required field '{required_key}' in home.json."
                        )
            elif path == "src/content/projects.json":
                if "projects" not in data or not isinstance(data["projects"], list):
                    raise InvalidFileContentError(
                        "projects.json must contain a 'projects' list."
                    )
                slugs: set[str] = set()
                for project in data["projects"]:
                    if not isinstance(project, dict) or "slug" not in project:
                        raise InvalidFileContentError(
                            "Each project in projects.json must have a 'slug'."
                        )
                    slug = str(project["slug"]).strip()
                    if slug in slugs:
                        raise InvalidFileContentError(
                            f"Duplicate project slug '{slug}' in projects.json."
                        )
                    slugs.add(slug)

        elif path.endswith(".css"):
            # CSS token security checks
            content_lower = content.lower()
            if "<script" in content_lower or "javascript:" in content_lower:
                raise InvalidFileContentError(
                    f"Malicious script injection detected in CSS file '{path}'."
                )
            if "@import" in content_lower and "fonts.googleapis.com" not in content:
                raise InvalidFileContentError(
                    f"Disallowed external @import found in CSS file '{path}'."
                )
