"""Configuration settings for Cloudflare Pages deployment and smoke testing."""

import os
import re

from pydantic import BaseModel, Field

PROJECT_NAME_CLEAN_REGEX = re.compile(r"[^a-zA-Z0-9-]")


def sanitize_project_name(name: str, prefix: str = "agency-") -> str:
    """Produce a deterministic, sanitized Cloudflare Pages project name.

    Constraints:
    - Lowercase alphanumeric characters and hyphens only.
    - Max 58 characters.
    """
    clean_name = PROJECT_NAME_CLEAN_REGEX.sub("-", name.strip().lower())
    if not clean_name.startswith(prefix):
        full_name = f"{prefix}{clean_name}"
    else:
        full_name = clean_name
    return full_name[:58]


class CloudflareSettings(BaseModel):
    """Validated settings for Cloudflare Pages API operations."""

    api_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "CLOUDFLARE_API_BASE_URL", "https://api.cloudflare.com/client/v4"
        ).rstrip("/")
    )
    api_token: str | None = Field(
        default_factory=lambda: os.getenv("CLOUDFLARE_API_TOKEN")
    )
    account_id: str = Field(
        default_factory=lambda: os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
    )
    project_prefix: str = Field(
        default_factory=lambda: os.getenv("CLOUDFLARE_PROJECT_PREFIX", "agency-")
    )
    production_branch: str = "main"
    request_timeout: float = 30.0
    polling_interval_seconds: float = 2.0
    max_wait_seconds: float = 60.0
    max_retries: int = 3

    def redact_token(self) -> str:
        """Return masked token representation safe for logging."""
        if not self.api_token:
            return "<none>"
        if len(self.api_token) <= 8:
            return "***"
        return f"{self.api_token[:4]}...{self.api_token[-4:]}"


class SmokeTestSettings(BaseModel):
    """Validated settings for post-deployment smoke testing and SSRF safety."""

    approved_hostnames: list[str] = Field(
        default_factory=lambda: [
            "*.pages.dev",
            "*.agency.run",
            "localhost",
            "127.0.0.1",
        ]
    )
    smoke_test_timeout: float = 10.0
    max_response_bytes: int = 2_097_152  # 2 MB upper bound
    allow_insecure_http: bool = Field(
        default_factory=lambda: (
            os.getenv("AGENCY_ALLOW_INSECURE_HTTP", "false").lower()
            in ("1", "true", "yes")
        )
    )
