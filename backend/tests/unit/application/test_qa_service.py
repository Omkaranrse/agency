"""Unit tests for the Phase 6 Automated QA Service and its individual checks."""

import json
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from tests.fakes.fake_sandbox import FakeSandbox

from agency.application.qa.checks.accessibility import AccessibilityCheck
from agency.application.qa.checks.build import BuildCheck
from agency.application.qa.checks.console import ConsoleCheck
from agency.application.qa.checks.html_validation import HtmlValidationCheck
from agency.application.qa.checks.lighthouse import LighthouseCheck
from agency.application.qa.checks.links import LinkCheck
from agency.application.qa.models import (
    CheckStatus,
    QAContext,
    SeverityLevel,
)
from agency.application.qa.service import QAService
from agency.application.qa.settings import QASettings
from agency.domain.entities.build_result import BuildResult

# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

DUMMY_COMMIT_SHA = "a" * 40


def _valid_html(
    title: str = "Test Title",
    lang: str = "en",
    h1: str = "Headline",
    body_extra: str = "",
    nav_links: str = "",
) -> str:
    """Generate minimal valid HTML5 markup for tests."""
    nav_html = f"<nav>{nav_links}</nav>" if nav_links else ""
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
</head>
<body>
    <header>{nav_html}</header>
    <main>
        <h1>{h1}</h1>
        {body_extra}
    </main>
</body>
</html>"""


# ---------------------------------------------------------------------------
# 1. Settings Validation
# ---------------------------------------------------------------------------


def test_qa_settings_defaults() -> None:
    """Verify default QA settings adhere to architectural requirements."""
    settings = QASettings()
    assert settings.required_routes == ["/", "/about/", "/projects/", "/contact/"]
    assert settings.enable_build_check is True
    assert settings.enable_console_check is True
    assert settings.enable_link_check is True
    assert settings.enable_html_check is True
    assert settings.enable_lighthouse_check is True
    assert settings.enable_accessibility_check is True
    assert settings.fail_on_critical is True
    assert settings.fail_on_serious is True
    assert settings.fail_on_moderate is False
    assert settings.fail_on_minor is False
    assert settings.allow_skipped_checks is False
    assert settings.lighthouse_performance_threshold == 80
    assert settings.lighthouse_accessibility_threshold == 90


def test_qa_settings_validation_errors() -> None:
    """Verify out-of-range thresholds or empty routes trigger validation errors."""
    with pytest.raises(ValidationError):
        QASettings(lighthouse_performance_threshold=-5)

    with pytest.raises(ValidationError):
        QASettings(lighthouse_accessibility_threshold=105)

    with pytest.raises(ValidationError):
        QASettings(required_routes=[])

    with pytest.raises(ValidationError):
        QASettings(max_issues_per_check=0)

    with pytest.raises(ValidationError):
        QASettings(navigation_timeout_ms=-100)


# ---------------------------------------------------------------------------
# 2. Build Check
# ---------------------------------------------------------------------------


def test_build_check_success() -> None:
    """Successful build with exit_code=0 and valid artifacts passes."""
    settings = QASettings()
    check = BuildCheck(settings)
    build_result = BuildResult(
        workspace_path="/workspace",
        commit_sha=DUMMY_COMMIT_SHA,
        build_ok=True,
        logs="Static site built successfully in 1.2s",
    )
    context = QAContext(
        run_id="run-1",
        build_result=build_result,
        artifacts=["index.html", "about/index.html"],
    )

    result = check.run(context)
    assert result.status == CheckStatus.PASSED
    assert result.passed is True
    assert "successfully" in result.details.lower()


def test_build_check_nonzero_exit() -> None:
    """Nonzero exit code reports failure with sanitized diagnostics."""
    settings = QASettings()
    check = BuildCheck(settings)
    build_result = BuildResult(
        workspace_path="/workspace",
        build_ok=False,
        logs="Error: Could not resolve dependency 'unknown-pkg'",
    )
    context = QAContext(run_id="run-1", build_result=build_result)

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "BUILD_NONZERO_EXIT"
    assert result.severity == SeverityLevel.CRITICAL
    assert "unknown-pkg" in result.details


def test_build_check_missing_artifacts() -> None:
    """Build with exit_code=0 but missing index.html fails artifact check."""
    settings = QASettings()
    check = BuildCheck(settings)
    build_result = BuildResult(
        workspace_path="/workspace",
        commit_sha=DUMMY_COMMIT_SHA,
        build_ok=True,
        logs="Done",
    )
    context = QAContext(
        run_id="run-1",
        build_result=build_result,
        artifacts=["assets/style.css"],  # Missing index.html
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "BUILD_MISSING_ARTIFACTS"


def test_build_check_missing_build_result() -> None:
    """Missing build result and missing local dist directory returns ERROR."""
    settings = QASettings()
    check = BuildCheck(settings)
    context = QAContext(run_id="run-1")

    result = check.run(context)
    assert result.status == CheckStatus.ERROR
    assert result.passed is False
    assert result.error_code == "BUILD_RESULT_UNAVAILABLE"


def test_build_check_secret_sanitization() -> None:
    """Sensitive tokens, credentials, and cookies are redacted from diagnostics."""
    settings = QASettings()
    check = BuildCheck(settings)
    build_result = BuildResult(
        workspace_path="/workspace",
        build_ok=False,
        logs=(
            "Error with Authorization: Bearer secret_token_xyz123 "
            "and password=super_secret"
        ),
    )
    context = QAContext(run_id="run-1", build_result=build_result)

    result = check.run(context)
    assert "secret_token_xyz123" not in result.details
    assert "super_secret" not in result.details
    assert "[REDACTED]" in result.details


def test_build_check_disabled() -> None:
    """Disabled check returns SKIPPED status."""
    settings = QASettings(enable_build_check=False)
    check = BuildCheck(settings)
    context = QAContext(run_id="run-1")

    result = check.run(context)
    assert result.status == CheckStatus.SKIPPED
    assert result.passed is True


# ---------------------------------------------------------------------------
# 3. Browser Console Check
# ---------------------------------------------------------------------------


def test_console_check_clean_events() -> None:
    """Zero browser console errors across all routes passes."""
    settings = QASettings()
    check = ConsoleCheck(settings)
    context = QAContext(
        run_id="run-1",
        routes=["/", "/about/"],
        browser_console_events={
            "/": [{"type": "info", "text": "Page rendered in 50ms"}],
            "/about/": [{"type": "log", "text": "Component mounted"}],
        },
    )

    result = check.run(context)
    assert result.status == CheckStatus.PASSED
    assert result.passed is True


def test_console_check_errors_detected() -> None:
    """Console error on a route fails the check with page and error code."""
    settings = QASettings()
    check = ConsoleCheck(settings)
    context = QAContext(
        run_id="run-1",
        routes=["/", "/contact/"],
        browser_console_events={
            "/": [],
            "/contact/": [
                {
                    "type": "error",
                    "text": "Uncaught TypeError: Cannot read properties of undefined",
                }
            ],
        },
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "BROWSER_CONSOLE_ERROR"
    assert result.page == "/contact/"
    assert "Uncaught TypeError" in result.details


def test_console_check_uncaught_page_exception() -> None:
    """Uncaught page exception is captured as a console error."""
    settings = QASettings()
    check = ConsoleCheck(settings)
    context = QAContext(
        run_id="run-1",
        routes=["/projects/"],
        browser_console_events={
            "/projects/": [
                {
                    "type": "pageerror",
                    "text": "ReferenceError: nonExistentFunction is not defined",
                }
            ]
        },
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "BROWSER_CONSOLE_ERROR"


def test_console_check_navigation_failed() -> None:
    """Navigation failure is captured with specific error code."""
    settings = QASettings()
    check = ConsoleCheck(settings)
    context = QAContext(
        run_id="run-1",
        routes=["/about/"],
        browser_console_events={
            "/about/": [
                {
                    "navigation_failed": True,
                    "text": "net::ERR_CONNECTION_REFUSED at http://localhost:4321/about/",
                }
            ]
        },
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "BROWSER_NAVIGATION_FAILED"


def test_console_check_failed_asset() -> None:
    """Required asset failure is captured with actionable asset error code."""
    settings = QASettings()
    check = ConsoleCheck(settings)
    context = QAContext(
        run_id="run-1",
        routes=["/"],
        browser_console_events={
            "/": [
                {
                    "failed_asset": True,
                    "text": "http://localhost:4321/_astro/main.xyz.js 404 (Not Found)",
                }
            ]
        },
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "BROWSER_ASSET_LOAD_FAILED"


def test_console_check_disabled() -> None:
    """Disabled check returns SKIPPED status."""
    settings = QASettings(enable_console_check=False)
    check = ConsoleCheck(settings)
    context = QAContext(run_id="run-1")

    result = check.run(context)
    assert result.status == CheckStatus.SKIPPED
    assert result.passed is True


# ---------------------------------------------------------------------------
# 4. Broken Internal Links Check
# ---------------------------------------------------------------------------


def test_link_check_valid_links() -> None:
    """Valid relative, absolute, and fragment links pass without errors."""
    settings = QASettings()
    check = LinkCheck(settings)

    html_home = _valid_html(
        body_extra=(
            '<a href="/about/">About</a>'
            '<a href="#services">Services</a>'
            '<section id="services">S</section>'
        )
    )
    html_about = _valid_html(
        body_extra='<a href="/">Home</a><a href="../contact/">Contact</a>'
    )
    html_contact = _valid_html(body_extra='<a href="/projects/">Projects</a>')
    html_projects = _valid_html(body_extra='<a href="/about/">About</a>')

    context = QAContext(
        run_id="run-1",
        routes=["/", "/about/", "/projects/", "/contact/"],
        rendered_pages_html={
            "/": html_home,
            "/about/": html_about,
            "/contact/": html_contact,
            "/projects/": html_projects,
        },
    )

    result = check.run(context)
    assert result.status == CheckStatus.PASSED
    assert result.passed is True


def test_link_check_broken_route() -> None:
    """Link targeting a nonexistent route fails with BROKEN_INTERNAL_LINK."""
    settings = QASettings()
    check = LinkCheck(settings)

    html_home = _valid_html(body_extra='<a href="/missing-page/">Missing</a>')
    html_about = _valid_html()

    context = QAContext(
        run_id="run-1",
        routes=["/", "/about/"],
        rendered_pages_html={"/": html_home, "/about/": html_about},
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "BROKEN_INTERNAL_LINK"
    assert result.page == "/"
    assert "/missing-page/" in result.details


def test_link_check_broken_fragment() -> None:
    """Fragment target #not-there missing on page fails validation."""
    settings = QASettings()
    check = LinkCheck(settings)

    html_home = _valid_html(body_extra='<a href="#nonexistent-anchor">Go</a>')

    context = QAContext(
        run_id="run-1",
        routes=["/"],
        rendered_pages_html={"/": html_home},
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "BROKEN_INTERNAL_LINK"
    assert "#nonexistent-anchor" in result.details


def test_link_check_external_links_ignored() -> None:
    """External links (https://...) are ignored and never trigger broken link errors."""
    settings = QASettings()
    check = LinkCheck(settings)

    html_home = _valid_html(
        body_extra=(
            '<a href="https://example.com/external">Ext</a>'
            '<a href="mailto:test@example.com">Mail</a>'
        )
    )

    context = QAContext(
        run_id="run-1",
        routes=["/"],
        rendered_pages_html={"/": html_home},
    )

    result = check.run(context)
    assert result.status == CheckStatus.PASSED
    assert result.passed is True


def test_link_check_missing_html_content() -> None:
    """Missing rendered HTML content returns ERROR status."""
    settings = QASettings()
    check = LinkCheck(settings)
    context = QAContext(run_id="run-1")

    result = check.run(context)
    assert result.status == CheckStatus.ERROR
    assert result.passed is False
    assert result.error_code == "HTML_PAGE_UNAVAILABLE"


def test_link_check_disabled() -> None:
    """Disabled link check returns SKIPPED."""
    settings = QASettings(enable_link_check=False)
    check = LinkCheck(settings)
    context = QAContext(run_id="run-1")

    result = check.run(context)
    assert result.status == CheckStatus.SKIPPED
    assert result.passed is True


# ---------------------------------------------------------------------------
# 5. HTML Validation Check
# ---------------------------------------------------------------------------


def test_html_validation_success() -> None:
    """Valid HTML5 markup across all pages passes."""
    settings = QASettings()
    check = HtmlValidationCheck(settings)
    context = QAContext(
        run_id="run-1",
        routes=["/", "/about/"],
        rendered_pages_html={
            "/": _valid_html(title="Home", h1="Welcome"),
            "/about/": _valid_html(title="About", h1="About Us"),
        },
    )

    result = check.run(context)
    assert result.status == CheckStatus.PASSED
    assert result.passed is True


def test_html_validation_missing_title() -> None:
    """HTML without a <title> element fails with HTML_MISSING_TITLE."""
    settings = QASettings()
    check = HtmlValidationCheck(settings)
    html_without_title = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body><h1>Headline</h1></body>
</html>"""
    context = QAContext(
        run_id="run-1",
        routes=["/"],
        rendered_pages_html={"/": html_without_title},
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "HTML_MISSING_TITLE"


def test_html_validation_missing_lang() -> None:
    """HTML missing the 'lang' attribute fails with HTML_MISSING_LANG."""
    settings = QASettings()
    check = HtmlValidationCheck(settings)
    html_without_lang = """<!DOCTYPE html>
<html>
<head><title>Title</title></head>
<body><h1>Headline</h1></body>
</html>"""
    context = QAContext(
        run_id="run-1",
        routes=["/"],
        rendered_pages_html={"/": html_without_lang},
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "HTML_MISSING_LANG"


def test_html_validation_duplicate_id() -> None:
    """HTML containing duplicate element IDs fails with HTML_DUPLICATE_ID."""
    settings = QASettings()
    check = HtmlValidationCheck(settings)
    html_duplicate_ids = _valid_html(
        body_extra='<div id="duplicate-id">One</div><div id="duplicate-id">Two</div>'
    )
    context = QAContext(
        run_id="run-1",
        routes=["/"],
        rendered_pages_html={"/": html_duplicate_ids},
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "HTML_DUPLICATE_ID"
    assert "duplicate-id" in result.details


def test_html_validation_missing_h1() -> None:
    """HTML lacking an <h1> element fails with HTML_MISSING_H1."""
    settings = QASettings()
    check = HtmlValidationCheck(settings)
    html_without_h1 = """<!DOCTYPE html>
<html lang="en">
<head><title>Title</title></head>
<body><h2>Only secondary heading</h2></body>
</html>"""
    context = QAContext(
        run_id="run-1",
        routes=["/"],
        rendered_pages_html={"/": html_without_h1},
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "HTML_MISSING_H1"


def test_html_validation_missing_html_content() -> None:
    """Missing HTML returns ERROR status."""
    settings = QASettings()
    check = HtmlValidationCheck(settings)
    context = QAContext(run_id="run-1")

    result = check.run(context)
    assert result.status == CheckStatus.ERROR
    assert result.passed is False
    assert result.error_code == "HTML_CONTENT_UNAVAILABLE"


def test_html_validation_disabled() -> None:
    """Disabled check returns SKIPPED."""
    settings = QASettings(enable_html_check=False)
    check = HtmlValidationCheck(settings)
    context = QAContext(run_id="run-1")

    result = check.run(context)
    assert result.status == CheckStatus.SKIPPED
    assert result.passed is True


# ---------------------------------------------------------------------------
# 6. Lighthouse CI Check
# ---------------------------------------------------------------------------


def test_lighthouse_check_success() -> None:
    """Scores satisfying all configured thresholds pass."""
    settings = QASettings(
        lighthouse_performance_threshold=80,
        lighthouse_accessibility_threshold=90,
        lighthouse_best_practices_threshold=85,
        lighthouse_seo_threshold=85,
    )
    check = LighthouseCheck(settings)
    context = QAContext(
        run_id="run-1",
        lighthouse_scores={
            "performance": 85,
            "accessibility": 95,
            "best_practices": 90,
            "seo": 92,
        },
    )

    result = check.run(context)
    assert result.status == CheckStatus.PASSED
    assert result.passed is True


def test_lighthouse_check_below_threshold() -> None:
    """Scores below configured threshold report failure with exact comparisons."""
    settings = QASettings(lighthouse_performance_threshold=80)
    check = LighthouseCheck(settings)
    context = QAContext(
        run_id="run-1",
        lighthouse_scores={
            "performance": 72,
            "accessibility": 95,
            "best_practices": 90,
            "seo": 90,
        },
    )

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "LIGHTHOUSE_THRESHOLD_FAILED"
    assert "performance" in result.details.lower()
    assert "72" in result.details and "80" in result.details


def test_lighthouse_check_missing_scores() -> None:
    """Missing Lighthouse scores return ERROR status (never silent pass)."""
    settings = QASettings()
    check = LighthouseCheck(settings)
    context = QAContext(run_id="run-1")

    result = check.run(context)
    assert result.status == CheckStatus.ERROR
    assert result.passed is False
    assert result.error_code == "LIGHTHOUSE_EXECUTION_ERROR"


def test_lighthouse_check_disabled() -> None:
    """Disabled check returns SKIPPED."""
    settings = QASettings(enable_lighthouse_check=False)
    check = LighthouseCheck(settings)
    context = QAContext(run_id="run-1")

    result = check.run(context)
    assert result.status == CheckStatus.SKIPPED
    assert result.passed is True


# ---------------------------------------------------------------------------
# 7. axe-core Accessibility Check
# ---------------------------------------------------------------------------


def test_accessibility_check_clean() -> None:
    """Zero accessibility violations passes cleanly."""
    settings = QASettings()
    check = AccessibilityCheck(settings)
    context = QAContext(run_id="run-1", axe_violations=[])

    result = check.run(context)
    assert result.status == CheckStatus.PASSED
    assert result.passed is True


def test_accessibility_check_critical_violation() -> None:
    """Critical violation causes immediate failure."""
    settings = QASettings()
    check = AccessibilityCheck(settings)
    violations = [
        {
            "id": "image-alt",
            "impact": "critical",
            "page": "/",
            "description": "Images must have alternate text",
            "helpUrl": "https://dequeuniversity.com/rules/axe/4.8/image-alt",
            "nodes": [{"target": ["img.hero-banner"]}],
        }
    ]
    context = QAContext(run_id="run-1", axe_violations=violations)

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "AXE_IMAGE_ALT"
    assert result.severity == SeverityLevel.CRITICAL
    assert "image-alt" in result.details
    assert "img.hero-banner" in result.details


def test_accessibility_check_serious_violation() -> None:
    """Serious violation causes failure under default policy."""
    settings = QASettings()
    check = AccessibilityCheck(settings)
    violations = [
        {
            "id": "color-contrast",
            "impact": "serious",
            "page": "/about/",
            "description": "Elements must have sufficient color contrast",
            "help": "Ensure contrast ratio meets WCAG 2 AA minimums",
            "nodes": [{"target": ["p.caption"]}],
        }
    ]
    context = QAContext(run_id="run-1", axe_violations=violations)

    result = check.run(context)
    assert result.status == CheckStatus.FAILED
    assert result.passed is False
    assert result.error_code == "AXE_COLOR_CONTRAST"
    assert result.severity == SeverityLevel.SERIOUS
    assert "color-contrast" in result.details


def test_accessibility_check_moderate_minor_policy() -> None:
    """Configurable gating for moderate and minor violations."""
    violations = [
        {
            "id": "landmark-complementary-is-top-level",
            "impact": "moderate",
            "page": "/",
            "description": "Complementary landmarks should be top-level",
            "nodes": [{"target": ["aside"]}],
        },
        {
            "id": "link-in-text-block",
            "impact": "minor",
            "page": "/",
            "description": "Links should be distinguishable without color alone",
            "nodes": [{"target": ["a.inline"]}],
        },
    ]

    # Default policy: fail_on_moderate=False, fail_on_minor=False -> PASSED
    settings_default = QASettings()
    check_default = AccessibilityCheck(settings_default)
    res_default = check_default.run(
        QAContext(run_id="run-1", axe_violations=violations)
    )
    assert res_default.status == CheckStatus.PASSED
    assert res_default.passed is True
    assert "moderate" in res_default.details

    # Strict policy: fail_on_moderate=True -> FAILED
    settings_strict = QASettings(fail_on_moderate=True)
    check_strict = AccessibilityCheck(settings_strict)
    res_strict = check_strict.run(QAContext(run_id="run-1", axe_violations=violations))
    assert res_strict.status == CheckStatus.FAILED
    assert res_strict.passed is False
    assert "landmark-complementary-is-top-level" in res_strict.details

    # Minor strict policy: fail_on_minor=True -> FAILED
    settings_minor_strict = QASettings(fail_on_minor=True)
    check_minor_strict = AccessibilityCheck(settings_minor_strict)
    res_minor_strict = check_minor_strict.run(
        QAContext(run_id="run-1", axe_violations=violations)
    )
    assert res_minor_strict.status == CheckStatus.FAILED
    assert res_minor_strict.passed is False


def test_accessibility_check_missing_violations_data() -> None:
    """Missing scanner output returns ERROR status."""
    settings = QASettings()
    check = AccessibilityCheck(settings)
    context = QAContext(run_id="run-1")  # axe_violations is None

    result = check.run(context)
    assert result.status == CheckStatus.ERROR
    assert result.passed is False
    assert result.error_code == "AXE_EXECUTION_ERROR"


def test_accessibility_check_disabled() -> None:
    """Disabled check returns SKIPPED."""
    settings = QASettings(enable_accessibility_check=False)
    check = AccessibilityCheck(settings)
    context = QAContext(run_id="run-1")

    result = check.run(context)
    assert result.status == CheckStatus.SKIPPED
    assert result.passed is True


# ---------------------------------------------------------------------------
# 8. QAService Orchestration & Aggregation
# ---------------------------------------------------------------------------


def test_qa_service_all_checks_pass() -> None:
    """When all 6 checks succeed, QAReport.overall_passed is True."""
    service = QAService()
    build_res = BuildResult(
        workspace_path="/workspace",
        commit_sha=DUMMY_COMMIT_SHA,
        build_ok=True,
        logs="Build succeeded",
    )
    html_home = _valid_html(body_extra='<a href="/about/">About</a>')
    html_about = _valid_html(body_extra='<a href="/">Home</a>')

    context = QAContext(
        run_id="run-test",
        build_result=build_res,
        artifacts=["index.html"],
        routes=["/", "/about/"],
        rendered_pages_html={"/": html_home, "/about/": html_about},
        browser_console_events={"/": [], "/about/": []},
        lighthouse_scores={
            "performance": 95,
            "accessibility": 98,
            "best_practices": 92,
            "seo": 95,
        },
        axe_violations=[],
    )

    report, results = service.run_with_results(context)
    assert len(results) == 6
    assert all(r.status == CheckStatus.PASSED for r in results)
    assert all(r.passed for r in results)
    assert report.overall_passed is True
    assert len(report.checks) == 6


def test_qa_service_one_failure_does_not_halt_other_checks() -> None:
    """Link check failure does not prevent subsequent checks from running."""
    service = QAService()
    build_res = BuildResult(
        workspace_path="/workspace",
        commit_sha=DUMMY_COMMIT_SHA,
        build_ok=True,
        logs="Build succeeded",
    )
    # Link check will fail due to link to /broken-link/
    html_home = _valid_html(body_extra='<a href="/broken-link/">Broken</a>')

    context = QAContext(
        run_id="run-test",
        build_result=build_res,
        artifacts=["index.html"],
        routes=["/"],
        rendered_pages_html={"/": html_home},
        browser_console_events={"/": []},
        lighthouse_scores={
            "performance": 90,
            "accessibility": 90,
            "best_practices": 90,
            "seo": 90,
        },
        axe_violations=[],
    )

    report, results = service.run_with_results(context)
    assert len(results) == 6

    # Verify link check failed
    link_res = next(r for r in results if r.name == "broken_internal_links")
    assert link_res.status == CheckStatus.FAILED
    assert link_res.passed is False

    # Verify other checks ran and passed
    build_check_res = next(r for r in results if r.name == "build_success")
    assert build_check_res.status == CheckStatus.PASSED
    assert build_check_res.passed is True

    html_check_res = next(r for r in results if r.name == "html_validation")
    assert html_check_res.status == CheckStatus.PASSED

    assert report.overall_passed is False


def test_qa_service_safely_catches_unexpected_exceptions() -> None:
    """Unhandled check exception is captured as ERROR without crashing."""
    service = QAService()

    # Mock a check that explodes
    exploding_check = MagicMock()
    exploding_check.NAME = "exploding_check"
    exploding_check.run.side_effect = RuntimeError("Fatal crash in check engine")

    context = QAContext(run_id="run-crash")
    result = service._execute_check_safely(exploding_check, context)

    assert result.status == CheckStatus.ERROR
    assert result.passed is False
    assert result.error_code == "CHECK_UNCAUGHT_EXCEPTION"
    assert "Fatal crash in check engine" in result.details


def test_qa_service_skipped_checks_policy() -> None:
    """Policy controls whether skipped checks allow overall pass."""
    # Build check passes, but console check disabled
    build_res = BuildResult(
        workspace_path="/workspace",
        commit_sha=DUMMY_COMMIT_SHA,
        build_ok=True,
        logs="ok",
    )
    html_home = _valid_html()

    base_context = QAContext(
        run_id="run-skip",
        build_result=build_res,
        artifacts=["index.html"],
        routes=["/"],
        rendered_pages_html={"/": html_home},
        lighthouse_scores={
            "performance": 90,
            "accessibility": 90,
            "best_practices": 90,
            "seo": 90,
        },
        axe_violations=[],
    )

    # 1. Disallow skipped checks (default): overall_passed is False
    settings_strict = QASettings(
        enable_console_check=False,
        allow_skipped_checks=False,
    )
    service_strict = QAService(settings_strict)
    report_strict, results_strict = service_strict.run_with_results(base_context)
    console_r = next(r for r in results_strict if r.name == "console_errors")
    assert console_r.status == CheckStatus.SKIPPED
    assert report_strict.overall_passed is False

    # 2. Allow skipped checks: overall_passed is True
    settings_lenient = QASettings(
        enable_console_check=False,
        allow_skipped_checks=True,
    )
    service_lenient = QAService(settings_lenient)
    report_lenient, _ = service_lenient.run_with_results(base_context)
    assert report_lenient.overall_passed is True


def test_qa_report_serializer_build_agent_json() -> None:
    """Serializer produces concise, valid JSON for future build agents."""
    service = QAService()
    build_res = BuildResult(
        workspace_path="/workspace",
        commit_sha=DUMMY_COMMIT_SHA,
        build_ok=True,
        logs="ok",
    )
    html_home = _valid_html(body_extra='<a href="/missing/">Missing</a>')

    context = QAContext(
        run_id="run-agent-json",
        build_result=build_res,
        artifacts=["index.html"],
        routes=["/"],
        rendered_pages_html={"/": html_home},
        browser_console_events={"/": []},
        lighthouse_scores={
            "performance": 95,
            "accessibility": 95,
            "best_practices": 95,
            "seo": 95,
        },
        axe_violations=[],
    )

    report, results, json_output = service.run_with_details(context)
    data = json.loads(json_output)

    assert data["run_id"] == "run-agent-json"
    assert data["overall_passed"] is False
    assert "checks" in data
    assert len(data["checks"]) == 6

    # Verify schema of checks
    link_entry = next(c for c in data["checks"] if c["name"] == "broken_internal_links")
    assert link_entry["passed"] is False
    assert link_entry["status"] == "failed"
    assert link_entry["error_code"] == "BROKEN_INTERNAL_LINK"
    assert link_entry["page"] == "/"
    assert "/missing/" in link_entry["details"]


def test_qa_service_with_fake_sandbox() -> None:
    """Service operates against FakeSandbox file read mechanism seamlessly."""
    sandbox = FakeSandbox()
    sandbox_id = sandbox.create("agency-sandbox:latest")

    # Populate files into sandbox
    sandbox.write_file(
        sandbox_id,
        "dist/index.html",
        _valid_html(title="Sandbox Home", h1="Welcome"),
    )
    sandbox.write_file(
        sandbox_id,
        "dist/about/index.html",
        _valid_html(title="Sandbox About", h1="About Us"),
    )

    build_res = BuildResult(
        workspace_path="/workspace",
        commit_sha=DUMMY_COMMIT_SHA,
        build_ok=True,
        logs="ok",
    )
    context = QAContext(
        run_id="run-sandbox",
        build_result=build_res,
        artifacts=["index.html"],
        routes=["/", "/about/"],
        sandbox=sandbox,
        sandbox_id=sandbox_id,
        browser_console_events={"/": [], "/about/": []},
        lighthouse_scores={
            "performance": 90,
            "accessibility": 90,
            "best_practices": 90,
            "seo": 90,
        },
        axe_violations=[],
    )

    service = QAService()
    report, results = service.run_with_results(context)

    html_res = next(r for r in results if r.name == "html_validation")
    assert html_res.status == CheckStatus.PASSED

    link_res = next(r for r in results if r.name == "broken_internal_links")
    assert link_res.status == CheckStatus.PASSED

    assert report.overall_passed is True
