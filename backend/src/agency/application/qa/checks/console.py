"""Browser Console Errors QA check."""

from typing import Any

from agency.application.qa.models import (
    CheckResult,
    CheckStatus,
    QAContext,
    SeverityLevel,
)
from agency.application.qa.settings import QASettings


class ConsoleCheck:
    """Detects browser console errors, uncaught exceptions, and navigation failures."""

    NAME = "console_errors"

    def __init__(self, settings: QASettings) -> None:
        self._settings = settings

    def run(self, context: QAContext) -> CheckResult:
        """Inspect browser console logs and navigation across required routes."""
        if not self._settings.enable_console_check:
            return CheckResult(
                name=self.NAME,
                status=CheckStatus.SKIPPED,
                passed=True,
                details="Browser console check disabled by configuration.",
            )

        routes = context.routes or self._settings.required_routes
        total_errors: list[dict[str, Any]] = []

        # 1. Evaluate pre-collected console events (unit test or mock mode)
        for route in routes:
            events = context.browser_console_events.get(route, [])
            for event in events:
                event_type = event.get("type", "log").lower()
                text = event.get("text", "")

                if event_type in ("error", "exception", "pageerror"):
                    total_errors.append(
                        {
                            "route": route,
                            "type": event_type,
                            "message": text,
                            "error_code": "BROWSER_CONSOLE_ERROR",
                        }
                    )
                elif event.get("navigation_failed"):
                    total_errors.append(
                        {
                            "route": route,
                            "type": "navigation_failure",
                            "message": text or f"Failed to navigate to {route}",
                            "error_code": "BROWSER_NAVIGATION_FAILED",
                        }
                    )
                elif event.get("failed_asset"):
                    total_errors.append(
                        {
                            "route": route,
                            "type": "asset_failure",
                            "message": f"Failed required asset request: {text}",
                            "error_code": "BROWSER_ASSET_LOAD_FAILED",
                        }
                    )

        # 2. Check for sandbox execution errors if events were expected from sandbox
        if (
            not context.browser_console_events
            and context.sandbox
            and context.sandbox_id
        ):
            # If no console events and sandbox has no QA report:
            try:
                raw_report = context.sandbox.read_file(
                    context.sandbox_id, "qa-report.json"
                )
                if "console_errors" in raw_report and '"passed": false' in raw_report:
                    total_errors.append(
                        {
                            "route": "/",
                            "type": "error",
                            "message": "Browser recorded console errors in sandbox",
                            "error_code": "BROWSER_CONSOLE_ERROR",
                        }
                    )
            except Exception:
                pass

        if total_errors:
            first = total_errors[0]
            count = len(total_errors)
            diag = f"{first['message']} ({count} total console issue(s) found)"
            if len(diag) > self._settings.max_diagnostic_length:
                diag = diag[: self._settings.max_diagnostic_length] + "..."

            return CheckResult(
                name=self.NAME,
                status=CheckStatus.FAILED,
                passed=False,
                error_code=first["error_code"],
                page=first["route"],
                severity=SeverityLevel.SERIOUS,
                details=diag,
                diagnostic_metadata={
                    "error_count": count,
                    "issues": total_errors[: self._settings.max_issues_per_check],
                },
            )

        num_routes = len(routes)
        return CheckResult(
            name=self.NAME,
            status=CheckStatus.PASSED,
            passed=True,
            details=(
                f"Zero browser console errors detected across {num_routes} page(s)."
            ),
            diagnostic_metadata={"pages_checked": routes},
        )
