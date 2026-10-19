"""Automated Quality Assurance Service."""

import logging
from typing import Protocol

from agency.application.qa.aggregation import QAAggregator, QAReportSerializer
from agency.application.qa.checks.accessibility import AccessibilityCheck
from agency.application.qa.checks.build import BuildCheck
from agency.application.qa.checks.console import ConsoleCheck
from agency.application.qa.checks.html_validation import HtmlValidationCheck
from agency.application.qa.checks.lighthouse import LighthouseCheck
from agency.application.qa.checks.links import LinkCheck
from agency.application.qa.models import (
    CheckResult,
    CheckStatus,
    QAContext,
    SeverityLevel,
)
from agency.application.qa.settings import QASettings
from agency.domain.entities.qa_report import QAReport

logger = logging.getLogger(__name__)


class QACheckProtocol(Protocol):
    """Protocol implemented by all modular QA check classes."""

    NAME: str

    def run(self, context: QAContext) -> CheckResult:
        """Run QA check and return result."""
        ...


class QAService:
    """Orchestrates independent QA checks and produces validated QAReports.

    Supported Checks:
    1. Build Success (exit code and artifact verification)
    2. Browser Console Errors (Playwright console and navigation error detection)
    3. Broken Internal Links (relative and normalized internal route verification)
    4. HTML Validation (HTML5 structural standards, title, lang, duplicate IDs, h1)
    5. Lighthouse CI (Performance, Accessibility, Best Practices, SEO scores)
    6. axe-core Accessibility Scan (automated WCAG 2.2 AA rule violation audit)
    """

    def __init__(self, settings: QASettings | None = None) -> None:
        self.settings = settings or QASettings()
        self.aggregator = QAAggregator(self.settings)

    def _execute_check_safely(
        self, check: QACheckProtocol, context: QAContext
    ) -> CheckResult:
        """Execute a check ensuring runtime exceptions are captured cleanly."""
        try:
            result: CheckResult = check.run(context)
            return result
        except Exception as exc:
            logger.exception(
                "Uncaught exception while executing QA check '%s'", check.NAME
            )
            return CheckResult(
                name=check.NAME,
                status=CheckStatus.ERROR,
                passed=False,
                error_code="CHECK_UNCAUGHT_EXCEPTION",
                severity=SeverityLevel.CRITICAL,
                details=f"Check encountered unexpected runtime error: {exc}",
                diagnostic_metadata={"exception_type": type(exc).__name__},
            )

    def run(self, context: QAContext) -> QAReport:
        """Run all configured QA checks and return an aggregated QAReport."""
        report, _ = self.run_with_results(context)
        return report

    def run_with_results(
        self, context: QAContext
    ) -> tuple[QAReport, list[CheckResult]]:
        """Run all checks and return domain QAReport and detailed CheckResults."""
        checks: list[QACheckProtocol] = [
            BuildCheck(self.settings),
            ConsoleCheck(self.settings),
            LinkCheck(self.settings),
            HtmlValidationCheck(self.settings),
            LighthouseCheck(self.settings),
            AccessibilityCheck(self.settings),
        ]

        results: list[CheckResult] = []

        for check in checks:
            result = self._execute_check_safely(check, context)
            results.append(result)

        report = self.aggregator.aggregate(results)
        return report, results

    def run_with_details(
        self, context: QAContext
    ) -> tuple[QAReport, list[CheckResult], str]:
        """Run checks and produce report, detailed results, and JSON."""
        report, results = self.run_with_results(context)
        build_agent_json = QAReportSerializer.to_build_agent_json(
            run_id=context.run_id,
            report=report,
            results=results,
        )
        return report, results, build_agent_json
