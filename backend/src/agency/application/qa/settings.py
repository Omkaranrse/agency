"""Configuration settings governing automated QA evaluation."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QASettings(BaseModel):
    """Validated settings controlling QA check execution and evaluation policies."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Routes to check
    required_routes: list[str] = Field(
        default_factory=lambda: ["/", "/about/", "/projects/", "/contact/"]
    )

    # Check enablement
    enable_build_check: bool = True
    enable_console_check: bool = True
    enable_link_check: bool = True
    enable_html_validation: bool = True
    enable_html_check: bool = True
    enable_lighthouse_check: bool = True
    enable_accessibility_check: bool = True

    # Execution bounds and timeouts
    navigation_timeout_seconds: float = Field(default=15.0, gt=0, le=300)
    navigation_timeout_ms: int = Field(default=15_000, gt=0, le=300_000)
    execution_timeout_seconds: float = Field(default=60.0, gt=0, le=600)

    # Lighthouse CI thresholds (normalized 0 to 100)
    lighthouse_performance_threshold: int = Field(default=80, ge=0, le=100)
    lighthouse_accessibility_threshold: int = Field(default=90, ge=0, le=100)
    lighthouse_best_practices_threshold: int = Field(default=80, ge=0, le=100)
    lighthouse_seo_threshold: int = Field(default=85, ge=0, le=100)

    # Accessibility policy
    fail_on_critical: bool = True
    fail_on_serious: bool = True
    fail_on_moderate: bool = False
    fail_on_minor: bool = False

    # Diagnostic & crawl bounds
    max_issues_per_check: int = Field(default=25, gt=0, le=100)
    max_diagnostic_length: int = Field(default=500, gt=0, le=5000)
    max_crawl_depth: int = Field(default=3, gt=0, le=10)
    max_pages_to_crawl: int = Field(default=20, gt=0, le=100)

    # Overall pass policy
    allow_skipped_checks: bool = False
    require_all_mandatory_checks: bool = True

    # Preview server configuration
    preview_base_url: str = "http://localhost:4321"

    @field_validator("required_routes")
    @classmethod
    def _validate_routes(cls, routes: list[str]) -> list[str]:
        if not routes:
            raise ValueError("At least one required route must be specified.")
        seen: set[str] = set()
        cleaned: list[str] = []
        for r in routes:
            stripped = r.strip()
            if not stripped.startswith("/"):
                raise ValueError(f"Route '{r}' must start with '/'.")
            if stripped in seen:
                raise ValueError(f"Duplicate route detected: '{r}'.")
            seen.add(stripped)
            cleaned.append(stripped)
        return cleaned
