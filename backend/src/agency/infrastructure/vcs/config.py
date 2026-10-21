"""Configuration settings for GitHub VCS integration."""

import os
import re

from pydantic import BaseModel, Field

REPO_NAME_CLEAN_REGEX = re.compile(r"[^a-zA-Z0-9._-]")


def sanitize_repo_name(name: str, prefix: str = "agency-") -> str:
    """Produce a deterministic, sanitized GitHub repository name.

    Constraints:
    - Alphanumeric characters, hyphens, underscores, and periods only.
    - Max 100 characters.
    """
    clean_name = REPO_NAME_CLEAN_REGEX.sub("-", name.strip().lower())
    if not clean_name.startswith(prefix):
        full_name = f"{prefix}{clean_name}"
    else:
        full_name = clean_name
    return full_name[:100]


class GitHubSettings(BaseModel):
    """Validated settings for GitHub API operations."""

    api_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "GITHUB_API_BASE_URL", "https://api.github.com"
        ).rstrip("/")
    )
    token: str | None = Field(
        default_factory=lambda: (
            os.getenv("GITHUB_TOKEN") or os.getenv("AGENCY_GITHUB_TOKEN")
        )
    )
    owner: str = Field(
        default_factory=lambda: os.getenv(
            "GITHUB_OWNER", os.getenv("AGENCY_GITHUB_OWNER", "")
        ).strip()
    )
    is_org: bool = Field(
        default_factory=lambda: (
            os.getenv("GITHUB_IS_ORG", "false").lower() in ("1", "true", "yes")
        )
    )
    private_by_default: bool = Field(
        default_factory=lambda: (
            os.getenv("AGENCY_GITHUB_PRIVATE_REPOS", "true").lower()
            in ("1", "true", "yes")
        )
    )
    request_timeout: float = 30.0
    max_retries: int = 3
    repo_prefix: str = Field(
        default_factory=lambda: os.getenv("AGENCY_GITHUB_REPO_PREFIX", "agency-")
    )

    def redact_token(self) -> str:
        """Return masked token representation safe for logging."""
        if not self.token:
            return "<none>"
        if len(self.token) <= 8:
            return "***"
        return f"{self.token[:4]}...{self.token[-4:]}"
