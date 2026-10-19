"""Lighthouse CI performance and audit QA check."""

from typing import Any

from agency.application.qa.models import (
    CheckResult,
    CheckStatus,
    QAContext,
    SeverityLevel,
)
from agency.application.qa.settings import QASettings


class LighthouseCheck:
    """Evaluates Lighthouse CI audits against configured performance, accessibility,

    best practices, and SEO thresholds.
    """

    NAME = "lighthouse"

    def __init__(self, settings: QASettings) -> None:
        self._settings = settings

    def run(self, context: QAContext) -> CheckResult:
        """Run Lighthouse score threshold comparisons."""
        if not self._settings.enable_lighthouse_check:
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.SKIPPED,
                passed=True,
                details="Lighthouse check disabled by configuration.",
            )

        thresholds = {
            "performance": self._settings.lighthouse_performance_threshold,
            "accessibility": self._settings.lighthouse_accessibility_threshold,
            "best_practices": self._settings.lighthouse_best_practices_threshold,
            "seo": self._settings.lighthouse_seo_threshold,
        }

        scores: dict[str, float] = dict(context.lighthouse_scores)

        # If not supplied directly, attempt reading from sandbox artifact
        if not scores and context.sandbox and context.sandbox_id:
            try:
                raw = context.sandbox.read_file(context.sandbox_id, "lighthouse.json")
                import json

                lh_data = json.loads(raw)
                # Parse normalized categories
                categories = lh_data.get("categories", {})
                for cat_name, cat_obj in categories.items():
                    key = cat_name.lower().replace("-", "_")
                    score_val = cat_obj.get("score")
                    if score_val is not None:
                        # Convert 0.0-1.0 to 0-100
                        scores[key] = round(score_val * 100, 1)
            except Exception:
                pass

        # If Lighthouse has not executed and no scores are available
        if not scores:
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.ERROR,
                passed=False,
                error_code="LIGHTHOUSE_EXECUTION_ERROR",
                severity=SeverityLevel.SERIOUS,
                details=(
                    "Lighthouse audit data is unavailable. The tool did not "
                    "execute or report."
                ),
            )

        failures: list[dict[str, Any]] = []
        comparisons: dict[str, Any] = {}

        for category, threshold in thresholds.items():
            actual = scores.get(category)
            if actual is None:
                failures.append(
                    {
                        "category": category,
                        "actual": None,
                        "threshold": threshold,
                        "reason": f"Missing score for category '{category}'",
                    }
                )
            else:
                comparisons[category] = {"score": actual, "threshold": threshold}
                if actual < threshold:
                    failures.append(
                        {
                            "category": category,
                            "actual": actual,
                            "threshold": threshold,
                            "reason": (
                                f"{category.capitalize()} score {actual} is below "
                                f"threshold {threshold}"
                            ),
                        }
                    )

        if failures:
            reasons = [f["reason"] for f in failures]
            diag = f"Lighthouse thresholds unmet: {'; '.join(reasons)}"
            if len(diag) > self._settings.max_diagnostic_length:
                diag = diag[: self._settings.max_diagnostic_length] + "..."

            return CheckResult(
                name=self.NAME,
                status=CheckStatus.FAILED,
                passed=False,
                error_code="LIGHTHOUSE_THRESHOLD_FAILED",
                severity=SeverityLevel.SERIOUS,
                details=diag,
                diagnostic_metadata={
                    "threshold_failures": failures,
                    "scores": scores,
                    "thresholds": thresholds,
                },
            )

        return CheckResult(
            name=self.NAME,
            status=CheckStatus.PASSED,
            passed=True,
            details=(
                f"All Lighthouse categories met configured thresholds: "
                f"Perf={scores.get('performance', 0)}, "
                f"A11y={scores.get('accessibility', 0)}, "
                f"BP={scores.get('best_practices', 0)}, "
                f"SEO={scores.get('seo', 0)}"
            ),
            diagnostic_metadata={"scores": scores, "thresholds": thresholds},
        )
