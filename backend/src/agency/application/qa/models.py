"""Domain-compatible models for the QA service."""

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agency.application.ports.sandbox import SandboxPort
from agency.domain.entities.qa_report import QACheck


class CheckStatus(StrEnum):
    """Execution status of an individual QA check."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"


class SeverityLevel(StrEnum):
    """Severity classification for quality and accessibility issues."""

    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"
    INFO = "info"


class CheckResult(BaseModel):
    """Result of an individual QA check execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    status: CheckStatus
    passed: bool
    details: str = Field(default="", max_length=10_000)
    error_code: str | None = Field(default=None, max_length=100)
    page: str | None = Field(default=None, max_length=500)
    severity: SeverityLevel | None = None
    diagnostic_metadata: dict[str, Any] = Field(default_factory=dict)

    def to_qa_check(self) -> QACheck:
        """Convert to domain QACheck entity."""
        return QACheck(
            name=self.name,
            passed=self.passed,
            details=self.details,
            status=self.status.value,
            error_code=self.error_code,
            page=self.page,
            severity=self.severity.value if self.severity else None,
            diagnostic_metadata=self.diagnostic_metadata,
        )


class QAContext(BaseModel):
    """Context and inputs supplied to the QA service and its checks."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: str = Field(min_length=1, max_length=100)
    project_id: str = Field(default="default", min_length=1, max_length=100)
    preview_base_url: str = "http://localhost:4321"
    routes: list[str] = Field(
        default_factory=lambda: ["/", "/about/", "/projects/", "/contact/"]
    )
    build_result: Any | None = None
    build_ok: bool | None = None
    build_exit_code: int = 0
    build_logs: str = ""
    artifacts: list[str] = Field(default_factory=list)
    dist_dir: Path | None = None
    site_dir: Path | None = None
    sandbox: SandboxPort | None = None
    sandbox_id: str | None = None

    # Pre-rendered or mock outputs for isolated unit testing
    rendered_pages_html: dict[str, str] = Field(default_factory=dict)
    browser_console_events: dict[str, list[dict[str, Any]]] = Field(
        default_factory=dict
    )
    lighthouse_scores: dict[str, float] = Field(default_factory=dict)
    axe_violations: list[dict[str, Any]] | None = None
