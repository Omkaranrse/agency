"""QA scorer evaluating automated test checks and mandatory pass criteria."""

from agency.domain.entities.qa_report import QAReport
from evals.schemas import QAScore


def score_qa(qa_report: QAReport | None) -> QAScore:
    """Evaluate QA results against mandatory pass criteria.

    Mandatory failures are never averaged into a passing result.
    """
    if qa_report is None or not qa_report.checks:
        return QAScore(
            executed_checks=0,
            passed_checks=0,
            failed_checks=0,
            skipped_checks=0,
            mandatory_passed=False,
            details="No QA report available or QA checks did not execute.",
        )

    executed = len(qa_report.checks)
    passed = sum(1 for c in qa_report.checks if c.passed)
    failed = sum(1 for c in qa_report.checks if not c.passed)
    skipped = sum(1 for c in qa_report.checks if getattr(c, "status", "") == "skipped")

    failed_names = [c.name for c in qa_report.checks if not c.passed]
    details = (
        f"All {executed} QA checks passed."
        if qa_report.overall_passed
        else f"QA failed on {failed} checks: {failed_names}"
    )

    return QAScore(
        executed_checks=executed,
        passed_checks=passed,
        failed_checks=failed,
        skipped_checks=skipped,
        mandatory_passed=qa_report.overall_passed,
        details=details,
    )
