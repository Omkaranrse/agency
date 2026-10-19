"""Unit tests for QAReport and QACheck domain entities."""

import pytest
from pydantic import ValidationError

from agency.domain.entities.qa_report import QACheck, QAReport


def mutate_attr(obj: object, name: str, value: object) -> None:
    """Helper to attempt dynamic mutation on frozen objects."""
    setattr(obj, name, value)


def test_valid_qa_report_all_passed() -> None:
    """Test valid QA report where all checks pass."""
    c1 = QACheck(name="Unit Tests", passed=True, details="24 tests passed")
    c2 = QACheck(name="Linter", passed=True, details="0 errors")
    report = QAReport(checks=[c1, c2])
    assert report.overall_passed is True
    assert len(report.checks) == 2


def test_qa_report_derived_overall_passed_false() -> None:
    """Test that overall_passed derives False when any check fails."""
    c1 = QACheck(name="Unit Tests", passed=True, details="24 tests passed")
    c2 = QACheck(name="E2E Tests", passed=False, details="Timeout on /contact")
    report = QAReport(checks=[c1, c2])
    assert report.overall_passed is False


def test_caller_cannot_force_overall_passed_true_on_failed_checks() -> None:
    """Test invariant: caller cannot override overall_passed=True when checks failed."""
    c1 = QACheck(name="Unit Tests", passed=True, details="ok")
    c2 = QACheck(name="Integration Tests", passed=False, details="DB error")
    with pytest.raises(ValidationError) as exc_info:
        QAReport(checks=[c1, c2], overall_passed=True)
    assert "Cannot mark QAReport as overall_passed=True" in str(exc_info.value)


def test_qa_report_rejects_empty_checks() -> None:
    """Test that an empty check list is rejected (cannot verify quality)."""
    with pytest.raises(ValidationError):
        QAReport(checks=[])


def test_qa_report_rejects_duplicate_check_names() -> None:
    """Test that duplicate check names within a report are rejected."""
    c1 = QACheck(name="Unit Tests", passed=True)
    c2 = QACheck(name="unit tests", passed=True)
    with pytest.raises(ValidationError) as exc_info:
        QAReport(checks=[c1, c2])
    assert "Duplicate QA check name" in str(exc_info.value)


def test_qa_report_is_immutable() -> None:
    """Test that QAReport and QACheck are immutable."""
    c = QACheck(name="Linter", passed=True)
    report = QAReport(checks=[c])
    with pytest.raises(ValidationError):
        mutate_attr(report, "overall_passed", False)

    with pytest.raises(ValidationError):
        mutate_attr(c, "passed", False)


def test_qa_check_extended_fields() -> None:
    """Test that QACheck supports machine-readable metadata fields."""
    c = QACheck(
        name="Console Errors",
        passed=False,
        details="Uncaught error on /contact",
        status="failed",
        error_code="BROWSER_CONSOLE_ERROR",
        page="/contact/",
        severity="serious",
        diagnostic_metadata={"count": 1},
    )
    assert c.status == "failed"
    assert c.error_code == "BROWSER_CONSOLE_ERROR"
    assert c.page == "/contact/"
    assert c.severity == "serious"
    assert c.diagnostic_metadata == {"count": 1}
    report = QAReport(checks=[c])
    assert report.overall_passed is False
