"""Build Success QA check."""

import re

from agency.application.qa.models import (
    CheckResult,
    CheckStatus,
    QAContext,
    SeverityLevel,
)
from agency.application.qa.settings import QASettings


def _sanitize_diagnostics(text: str, max_length: int) -> str:
    """Sanitize secrets and limit diagnostic length."""
    sanitized = text
    # Key-value credentials
    sanitized = re.sub(
        r"(?i)(password|passwd|secret|token|apikey)\s*[:=]\s*[^\s]+",
        r"\1=[REDACTED]",
        sanitized,
    )
    # Bearer tokens
    sanitized = re.sub(
        r"(?i)bearer\s+[a-zA-Z0-9_\-\.]+",
        "Bearer [REDACTED]",
        sanitized,
    )
    # GitHub personal tokens
    sanitized = re.sub(r"ghp_[a-zA-Z0-9]{36}", "ghp_[REDACTED]", sanitized)
    # JWTs
    sanitized = re.sub(
        r"ey[a-zA-Z0-9_-]{10,}\.ey[a-zA-Z0-9_-]{10,}(\.[a-zA-Z0-9_-]*)?",
        "[REDACTED_JWT]",
        sanitized,
    )
    if len(sanitized) > max_length:
        return sanitized[:max_length] + "... [truncated]"
    return sanitized


class BuildCheck:
    """Verifies that the static site production build succeeded."""

    NAME = "build_success"

    def __init__(self, settings: QASettings) -> None:
        self._settings = settings

    def run(self, context: QAContext) -> CheckResult:
        """Execute build verification check."""
        if not self._settings.enable_build_check:
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.SKIPPED,
                passed=True,
                details="Build check disabled by configuration.",
            )

        # 1. Resolve build status
        build_result = context.build_result
        if build_result is not None:
            build_ok = getattr(build_result, "build_ok", True)
            exit_code = getattr(build_result, "exit_code", 0 if build_ok else 1)
            raw_logs = getattr(build_result, "logs", "")
            artifacts = getattr(build_result, "artifacts", context.artifacts)
        elif context.build_ok is not None:
            build_ok = context.build_ok
            exit_code = context.build_exit_code
            raw_logs = context.build_logs
        elif (
            context.dist_dir
            or context.site_dir
            or (context.sandbox and context.sandbox_id)
        ):
            build_ok = True
            exit_code = 0
            raw_logs = context.build_logs
            artifacts = context.artifacts
        else:
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.ERROR,
                passed=False,
                error_code="BUILD_RESULT_UNAVAILABLE",
                severity=SeverityLevel.SERIOUS,
                details="Build result data is unavailable for evaluation.",
            )

        # 2. Verify exit code and build status
        if not build_ok or exit_code != 0:
            raw_diag = raw_logs.strip() or f"Build failed with exit code {exit_code}."
            diag = _sanitize_diagnostics(raw_diag, self._settings.max_diagnostic_length)
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.FAILED,
                passed=False,
                error_code="BUILD_NONZERO_EXIT",
                severity=SeverityLevel.CRITICAL,
                details=f"Production build exited with error: {diag}",
                diagnostic_metadata={"exit_code": exit_code, "build_ok": build_ok},
            )

        # 3. Verify build output artifact existence
        missing_artifacts: list[str] = []
        if artifacts and "index.html" not in [a.lstrip("/") for a in artifacts]:
            missing_artifacts.append("index.html")

        if context.dist_dir and not (context.dist_dir / "index.html").is_file():
            missing_artifacts.append(f"{context.dist_dir}/index.html")
        elif context.site_dir and not (context.site_dir / "index.html").is_file():
            missing_artifacts.append(f"{context.site_dir}/index.html")
        elif context.sandbox and context.sandbox_id:
            try:
                content = context.sandbox.read_file(
                    context.sandbox_id, "dist/index.html"
                )
                if not content:
                    missing_artifacts.append("dist/index.html (empty)")
            except Exception:
                missing_artifacts.append("dist/index.html")

        if missing_artifacts:
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.FAILED,
                passed=False,
                error_code="BUILD_MISSING_ARTIFACTS",
                severity=SeverityLevel.CRITICAL,
                details=(
                    "Production build succeeded but expected artifacts were missing: "
                    f"{', '.join(missing_artifacts)}"
                ),
            )

        return CheckResult(
            name=self.NAME,
            status=CheckStatus.PASSED,
            passed=True,
            details="Production build completed successfully with verified artifacts.",
        )
