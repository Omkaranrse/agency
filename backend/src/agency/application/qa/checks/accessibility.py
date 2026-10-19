"""axe-core Accessibility Scan QA check."""

from typing import Any

from agency.application.qa.models import (
    CheckResult,
    CheckStatus,
    QAContext,
    SeverityLevel,
)
from agency.application.qa.settings import QASettings


def _sanitize_selector(selector: str, max_length: int = 120) -> str:
    """Sanitize CSS selector for clean logging without sensitive text."""
    clean = selector.strip()
    if len(clean) > max_length:
        return clean[:max_length] + "..."
    return clean


class AccessibilityCheck:
    """Evaluates automated accessibility compliance using axe-core rule violations.

    Note:
        Automated accessibility scans identify approximately 30-50% of WCAG issues.
        Automated scanning does not replace manual keyboard navigation, screen-reader,
        and assistive-technology testing.
    """

    NAME = "accessibility"

    def __init__(self, settings: QASettings) -> None:
        self._settings = settings

    def run(self, context: QAContext) -> CheckResult:
        """Analyze accessibility scan violations against configured severity policy."""
        if not self._settings.enable_accessibility_check:
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.SKIPPED,
                passed=True,
                details="Accessibility check disabled by configuration.",
            )

        violations: list[dict[str, Any]] = []
        has_axe_data = False

        if context.axe_violations is not None:
            violations = list(context.axe_violations)
            has_axe_data = True
        elif context.sandbox and context.sandbox_id:
            try:
                raw = context.sandbox.read_file(context.sandbox_id, "axe-report.json")
                import json

                axe_data = json.loads(raw)
                if isinstance(axe_data, list):
                    violations.extend(axe_data)
                elif isinstance(axe_data, dict):
                    violations.extend(axe_data.get("violations", []))
                has_axe_data = True
            except Exception:
                pass

        if not has_axe_data:
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.ERROR,
                passed=False,
                error_code="AXE_EXECUTION_ERROR",
                severity=SeverityLevel.SERIOUS,
                details="axe-core accessibility scanner did not execute or report.",
            )

        # Categorize violations by severity impact
        critical_violations: list[dict[str, Any]] = []
        serious_violations: list[dict[str, Any]] = []
        moderate_violations: list[dict[str, Any]] = []
        minor_violations: list[dict[str, Any]] = []

        for v in violations:
            rule_id = v.get("id") or v.get("rule_id", "unknown_rule")
            impact = (v.get("impact") or "moderate").lower()
            page = v.get("page") or v.get("route", "/")
            help_msg = v.get("help") or v.get(
                "description", "Accessibility rule violation"
            )
            nodes = v.get("nodes", [])
            selector = ""
            if nodes and isinstance(nodes, list) and isinstance(nodes[0], dict):
                target = nodes[0].get("target", [])
                if target and isinstance(target, list):
                    selector = _sanitize_selector(str(target[0]))

            entry = {
                "rule_id": rule_id,
                "impact": impact,
                "page": page,
                "description": help_msg,
                "selector": selector,
            }

            if impact == "critical":
                critical_violations.append(entry)
            elif impact == "serious":
                serious_violations.append(entry)
            elif impact == "moderate":
                moderate_violations.append(entry)
            else:
                minor_violations.append(entry)

        # Determine failures based on configured policy
        blocking_violations: list[dict[str, Any]] = []
        if self._settings.fail_on_critical:
            blocking_violations.extend(critical_violations)
        if self._settings.fail_on_serious:
            blocking_violations.extend(serious_violations)
        if self._settings.fail_on_moderate:
            blocking_violations.extend(moderate_violations)
        if self._settings.fail_on_minor:
            blocking_violations.extend(minor_violations)

        total_violations_count = len(violations)

        if blocking_violations:
            first = blocking_violations[0]
            count = len(blocking_violations)
            desc = first["description"]
            sel = first["selector"]
            diag = (
                f"[{first['impact'].upper()}] {first['rule_id']} on {first['page']}: "
                f"{desc} (Selector: '{sel}') [{count} blocking violation(s)]"
            )
            if len(diag) > self._settings.max_diagnostic_length:
                diag = diag[: self._settings.max_diagnostic_length] + "..."

            # Map impact to SeverityLevel
            sev_map = {
                "critical": SeverityLevel.CRITICAL,
                "serious": SeverityLevel.SERIOUS,
                "moderate": SeverityLevel.MODERATE,
                "minor": SeverityLevel.MINOR,
            }
            severity = sev_map.get(first["impact"], SeverityLevel.SERIOUS)

            return CheckResult(
                name=self.NAME,
                status=CheckStatus.FAILED,
                passed=False,
                error_code=f"AXE_{first['rule_id'].upper().replace('-', '_')}",
                page=first["page"],
                severity=severity,
                details=diag,
                diagnostic_metadata={
                    "blocking_count": count,
                    "critical_count": len(critical_violations),
                    "serious_count": len(serious_violations),
                    "moderate_count": len(moderate_violations),
                    "minor_count": len(minor_violations),
                    "violations": blocking_violations[
                        : self._settings.max_issues_per_check
                    ],
                },
            )

        # If only non-blocking violations exist (e.g. moderate/minor advisory)
        mod_count = len(moderate_violations)
        min_count = len(minor_violations)
        if total_violations_count > 0:
            details = (
                f"Zero blocking accessibility violations detected ({mod_count} "
                f"moderate, {min_count} minor advisory notice(s))."
            )
        else:
            details = "Zero automated accessibility violations detected by axe-core."

        return CheckResult(
            name=self.NAME,
            status=CheckStatus.PASSED,
            passed=True,
            details=details,
            diagnostic_metadata={
                "critical_count": 0,
                "serious_count": 0,
                "moderate_count": len(moderate_violations),
                "minor_count": len(minor_violations),
            },
        )
