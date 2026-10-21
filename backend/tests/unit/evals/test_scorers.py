"""Unit tests for metric scorers: build, QA, Lighthouse, cost, and copy quality."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from evals.scorers.build import score_build
from evals.scorers.copy_quality import score_copy_quality
from evals.scorers.cost import score_cost
from evals.scorers.duration import score_duration
from evals.scorers.lighthouse import score_lighthouse
from evals.scorers.qa import score_qa
from pydantic import HttpUrl

from agency.domain.entities.brief import Brief
from agency.domain.entities.qa_report import QACheck, QAReport


def test_score_build_detects_exit_code_and_artifacts(tmp_path: Path) -> None:
    """Build scorer verifies exit code, index.html existence, and requested routes."""
    # 1. Failure on non-zero exit code
    score_fail_exit = score_build(exit_code=1, artifact_dir=tmp_path)
    assert not score_fail_exit.success
    assert score_fail_exit.exit_code == 1

    # 2. Failure on missing artifact directory
    score_missing_dir = score_build(exit_code=0, artifact_dir=None)
    assert not score_missing_dir.success

    # 3. Failure on missing index.html
    score_no_index = score_build(exit_code=0, artifact_dir=tmp_path)
    assert not score_no_index.success
    assert not score_no_index.artifacts_present

    # 4. Succeeded build with artifacts and routes
    (tmp_path / "index.html").write_text("<h1>Home</h1>")
    (tmp_path / "about.html").write_text("<h1>About</h1>")
    (tmp_path / "contact.html").write_text("<h1>Contact</h1>")

    score_ok = score_build(
        exit_code=0,
        artifact_dir=tmp_path,
        required_routes=["about.html", "contact.html"],
    )
    assert score_ok.success
    assert score_ok.artifacts_present
    assert score_ok.required_routes_present


def test_score_qa_enforces_mandatory_pass_criteria() -> None:
    """QA scorer rejects runs with missing or failed mandatory checks."""
    # None report
    score_none = score_qa(None)
    assert not score_none.mandatory_passed
    assert score_none.executed_checks == 0

    # Passed report
    passed_checks = [
        QACheck(name="build_success", passed=True, status="passed"),
        QACheck(name="tokens_valid", passed=True, status="passed"),
    ]
    report_pass = QAReport(checks=passed_checks, overall_passed=True)
    score_pass = score_qa(report_pass)
    assert score_pass.mandatory_passed
    assert score_pass.passed_checks == 2
    assert score_pass.failed_checks == 0

    # Failed report
    failed_checks = [
        QACheck(name="build_success", passed=True, status="passed"),
        QACheck(name="links_working", passed=False, status="failed"),
    ]
    report_fail = QAReport(checks=failed_checks, overall_passed=False)
    score_fail = score_qa(report_fail)
    assert not score_fail.mandatory_passed
    assert score_fail.failed_checks == 1


def test_score_lighthouse_handles_unavailable_gracefully() -> None:
    """Lighthouse scorer explicitly marks unavailable without fabricating scores."""
    # When build failed
    score_unbuilt = score_lighthouse(
        site_url="http://localhost:4321", build_succeeded=False
    )
    assert not score_unbuilt.available
    assert "Build failed" in (score_unbuilt.reason_unavailable or "")

    # When no binary is installed
    with patch("shutil.which", return_value=None):
        score_no_cli = score_lighthouse(
            site_url="http://localhost:4321", build_succeeded=True
        )
        assert not score_no_cli.available
        assert "not found" in (score_no_cli.reason_unavailable or "")


def test_score_cost_distinguishes_fake_and_real() -> None:
    """Cost scorer sets actual cost to zero in fake mode and computes real estimates."""
    # Fake mode
    fake_cost = score_cost(input_tokens=1000, output_tokens=500, is_fake_mode=True)
    assert fake_cost.actual_cost_usd == 0.0
    assert fake_cost.estimated_cost_usd == 0.0

    # Real mode
    real_cost = score_cost(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        is_fake_mode=False,
        model="gemini-1.5-pro",
        provider_cost_usd=6.25,
    )
    assert real_cost.actual_cost_usd == 6.25
    assert real_cost.estimated_cost_usd > 0.0
    assert real_cost.cost_per_successful_build == 6.25


def test_score_duration_uses_monotonic_time() -> None:
    """Duration scorer measures elapsed time using monotonic clock values."""
    start_wall = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    end_wall = datetime(2026, 1, 1, 12, 0, 5, tzinfo=UTC)

    duration = score_duration(
        start_monotonic=100.0,
        end_monotonic=104.5,
        start_wall=start_wall,
        end_wall=end_wall,
        build_seconds=2.1,
        qa_seconds=1.4,
    )
    assert duration.elapsed_monotonic_seconds == 4.5
    assert duration.total_wall_clock_seconds == 5.0
    assert duration.build_seconds == 2.1
    assert duration.qa_seconds == 1.4


def test_score_copy_quality_penalizes_placeholders_and_unsupported_claims() -> None:
    """Copy quality rubric accurately scores content and detects placeholders."""
    brief = Brief(
        client_name="Maya Lin",
        site_type="Architecture Portfolio",
        pages=["Home", "Work", "About", "Contact"],
        tone="minimal",
        content_notes=(
            "Memorial architect focused on landscape art and sustainable "
            "museum designs."
        ),
        links=[HttpUrl("https://example.com/mayalin")],
    )

    # 1. Clean content conforming to brief
    clean_pages = [
        {
            "page_slug": "home",
            "title": "Maya Lin — Architecture Portfolio",
            "headline": "Sculptural landscape art and sustainable museum designs",
            "content": (
                "Memorial architect Maya Lin creates contemplative spaces "
                "connecting landscape, architecture, and environmental memory."
            ),
        },
        {
            "page_slug": "work",
            "title": "Selected Works",
            "content": (
                "A focused retrospective of sustainable pavilions and memorials."
            ),
        },
        {
            "page_slug": "about",
            "title": "About Maya Lin",
            "content": ("Refined architectural inquiry exploring minimal structures."),
        },
        {
            "page_slug": "contact",
            "title": "Contact",
            "content": "Studio inquiries for museum commissions.",
        },
    ]
    clean_score = score_copy_quality(brief, clean_pages)
    assert clean_score.passed
    assert clean_score.overall_score >= 7.5
    assert clean_score.absence_of_placeholders == 10.0
    assert len(clean_score.detected_placeholders) == 0

    # 2. Content with placeholders -> must fail absence_of_placeholders
    dirty_pages = [
        {
            "page_slug": "home",
            "title": "Home",
            "content": (
                "Lorem ipsum dolor sit amet. TODO: insert here the bio. "
                "Coming soon [Your Name]."
            ),
        }
    ]
    dirty_score = score_copy_quality(brief, dirty_pages)
    assert not dirty_score.passed
    assert dirty_score.absence_of_placeholders < 5.0
    assert len(dirty_score.detected_placeholders) > 0
