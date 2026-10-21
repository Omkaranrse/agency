"""Deterministic in-memory FakeQAService for testing workflow orchestration."""

from agency.application.qa.models import QAContext
from agency.application.qa.service import QAService
from agency.domain.entities.qa_report import QACheck, QAReport


def make_passing_qa_report() -> QAReport:
    """Create a default passing QAReport with all standard checks."""
    checks = [
        QACheck(name="build_success", passed=True, status="passed"),
        QACheck(name="console_errors", passed=True, status="passed"),
        QACheck(name="broken_internal_links", passed=True, status="passed"),
        QACheck(name="html_validation", passed=True, status="passed"),
        QACheck(name="lighthouse", passed=True, status="passed"),
        QACheck(name="accessibility", passed=True, status="passed"),
    ]
    return QAReport(checks=checks, overall_passed=True)


def make_failing_qa_report(
    failing_checks: list[str] | None = None,
) -> QAReport:
    """Create a failing QAReport with specified failing checks."""
    failed = set(failing_checks or ["accessibility"])
    checks = [
        QACheck(
            name="build_success",
            passed="build_success" not in failed,
            status="failed" if "build_success" in failed else "passed",
        ),
        QACheck(
            name="console_errors",
            passed="console_errors" not in failed,
            status="failed" if "console_errors" in failed else "passed",
        ),
        QACheck(
            name="broken_internal_links",
            passed="broken_internal_links" not in failed,
            status="failed" if "broken_internal_links" in failed else "passed",
        ),
        QACheck(
            name="html_validation",
            passed="html_validation" not in failed,
            status="failed" if "html_validation" in failed else "passed",
        ),
        QACheck(
            name="lighthouse",
            passed="lighthouse" not in failed,
            status="failed" if "lighthouse" in failed else "passed",
        ),
        QACheck(
            name="accessibility",
            passed="accessibility" not in failed,
            status="failed" if "accessibility" in failed else "passed",
            details="Color contrast ratio failure on primary button.",
        ),
    ]
    return QAReport(checks=checks, overall_passed=False)


class FakeQAService(QAService):
    """Deterministic QA test fake for workflow orchestration tests."""

    def __init__(self, default_report: QAReport | None = None) -> None:
        super().__init__()
        self._reports_queue: list[QAReport] = []
        self._default_report = default_report or make_passing_qa_report()
        self.calls: list[QAContext] = []

    def set_report(self, report: QAReport) -> None:
        """Set default report returned when queue is empty."""
        self._default_report = report

    def enqueue_report(self, report: QAReport) -> None:
        """Enqueue a specific report for subsequent run invocations."""
        self._reports_queue.append(report)

    def run(self, context: QAContext) -> QAReport:
        """Return next queued report or default report, capturing context."""
        self.calls.append(context)
        if self._reports_queue:
            return self._reports_queue.pop(0)
        return self._default_report
