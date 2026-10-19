"""Build Result domain entity."""

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-fA-F]{7,40}$")


class BuildResult(BaseModel):
    """Represents the outcome of a code compilation/build executed externally."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_path: str = Field(min_length=1, max_length=500)
    commit_sha: str | None = Field(default=None)
    build_ok: bool
    logs: str = Field(default="", max_length=100_000)

    @field_validator("workspace_path", mode="before")
    @classmethod
    def _strip_workspace_path(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Workspace path cannot be empty.")
            return stripped
        return value

    @field_validator("commit_sha", mode="before")
    @classmethod
    def _validate_commit_sha(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if not COMMIT_SHA_PATTERN.match(stripped):
                raise ValueError(
                    f"Invalid commit SHA format '{value}'. "
                    "Expected 7-40 hexadecimal characters."
                )
            return stripped.lower()
        return value

    @field_validator("logs", mode="before")
    @classmethod
    def _enforce_log_policy(cls, value: object) -> object:
        if isinstance(value, str):
            # Limit logs to 100_000 chars (preserving the tail summary)
            if len(value) > 100_000:
                truncated_notice = "[... logs truncated by domain policy ...]\n"
                tail_len = 100_000 - len(truncated_notice)
                return truncated_notice + value[-tail_len:]
            return value
        return value

    @model_validator(mode="after")
    def _validate_build_metadata(self) -> Self:
        if self.build_ok:
            if not self.commit_sha:
                raise ValueError(
                    "A successful build (build_ok=True) must be linked "
                    "to a valid commit SHA."
                )
            if not self.workspace_path:
                raise ValueError(
                    "A successful build must specify a non-empty workspace path."
                )
        return self
