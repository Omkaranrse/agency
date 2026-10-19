"""Aggregation and serialization for QA check results."""

import json
from typing import Any

from agency.application.qa.models import CheckResult, CheckStatus
from agency.application.qa.settings import QASettings
from agency.domain.entities.qa_report import QACheck, QAReport


class QAAggregator:
    """Aggregates individual check outcomes into the domain QAReport aggregate."""

    def __init__(self, settings: QASettings) -> None:
        self._settings = settings

    def aggregate(self, results: list[CheckResult]) -> QAReport:
        """Deterministically aggregate check results into a validated QAReport."""
        if not results:
            raise ValueError("Cannot aggregate an empty list of QA check results.")

        domain_checks: list[QACheck] = []

        for r in results:
            passed = r.passed
            # If check errored or failed, it cannot pass
            if r.status in (CheckStatus.FAILED, CheckStatus.ERROR):
                passed = False
            elif r.status == CheckStatus.SKIPPED:
                # If skipped checks are disallowed by policy, mark as failed
                if not self._settings.allow_skipped_checks:
                    passed = False

            domain_check = QACheck(
                name=r.name,
                passed=passed,
                details=r.details,
                status=r.status.value,
                error_code=r.error_code,
                page=r.page,
                severity=r.severity.value if r.severity else None,
                diagnostic_metadata=r.diagnostic_metadata,
            )
            domain_checks.append(domain_check)

        overall_passed = bool(domain_checks and all(c.passed for c in domain_checks))

        return QAReport(checks=domain_checks, overall_passed=overall_passed)


class QAReportSerializer:
    """Formats and serializes QA evaluations into machine-readable JSON."""

    @classmethod
    def to_build_agent_dict(
        cls,
        run_id: str,
        report: QAReport,
        results: list[CheckResult] | None = None,
    ) -> dict[str, Any]:
        """Convert QA report into a structured, machine-readable dictionary."""
        checks_data: list[dict[str, Any]] = []

        if results:
            for r in results:
                entry: dict[str, Any] = {
                    "name": r.name,
                    "passed": r.passed and r.status == CheckStatus.PASSED,
                    "status": r.status.value,
                    "details": r.details,
                }
                if r.error_code:
                    entry["error_code"] = r.error_code
                if r.page:
                    entry["page"] = r.page
                if r.severity:
                    entry["severity"] = r.severity.value
                if r.diagnostic_metadata:
                    entry["metadata"] = r.diagnostic_metadata
                checks_data.append(entry)
        else:
            for c in report.checks:
                entry = {
                    "name": c.name,
                    "passed": c.passed,
                    "status": c.status,
                    "details": c.details,
                }
                if c.error_code:
                    entry["error_code"] = c.error_code
                if c.page:
                    entry["page"] = c.page
                if c.severity:
                    entry["severity"] = c.severity
                if c.diagnostic_metadata:
                    entry["metadata"] = c.diagnostic_metadata
                checks_data.append(entry)

        # Sort checks deterministically by name
        checks_data.sort(key=lambda x: str(x.get("name", "")))

        passed_count = sum(1 for c in checks_data if c["passed"])
        failed_count = sum(1 for c in checks_data if c.get("status") == "failed")
        error_count = sum(1 for c in checks_data if c.get("status") == "error")
        skipped_count = sum(1 for c in checks_data if c.get("status") == "skipped")

        return {
            "run_id": run_id,
            "overall_passed": report.overall_passed,
            "summary": {
                "total_checks": len(checks_data),
                "passed_checks": passed_count,
                "failed_checks": failed_count,
                "error_checks": error_count,
                "skipped_checks": skipped_count,
            },
            "checks": checks_data,
        }

    @classmethod
    def to_build_agent_json(
        cls,
        run_id: str,
        report: QAReport,
        results: list[CheckResult] | None = None,
        indent: int = 2,
    ) -> str:
        """Produce machine-readable JSON string suitable for build agent inputs."""
        data = cls.to_build_agent_dict(run_id, report, results)
        return json.dumps(data, indent=indent, default=str)
