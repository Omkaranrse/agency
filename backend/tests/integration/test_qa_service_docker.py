"""Integration tests for QAService operating within a Docker sandbox."""

import json
from pathlib import Path

import pytest

from agency.application.qa.models import CheckResult, CheckStatus, QAContext
from agency.application.qa.service import QAService
from agency.domain.entities.build_result import BuildResult
from agency.domain.entities.qa_report import QAReport
from agency.infrastructure.sandbox.docker_sandbox import DockerSandbox
from agency.infrastructure.sandbox.models import SandboxConfig


def _check_docker() -> tuple[bool, str]:
    """Check if Docker SDK is installed, daemon is responsive, and image exists."""
    try:
        import docker

        client = docker.from_env()
        client.ping()
        try:
            client.images.get("agency-sandbox:latest")
        except Exception as exc:
            return (
                False,
                f"Required sandbox image 'agency-sandbox:latest' not found: {exc}",
            )
        return True, "Docker daemon responsive and image available"
    except Exception as exc:
        return False, f"Docker daemon unavailable: {exc}"


DOCKER_AVAILABLE, DOCKER_REASON = _check_docker()

pytestmark = [
    pytest.mark.docker,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=DOCKER_REASON),
]


def test_qa_service_in_docker_sandbox(tmp_path: Path) -> None:
    """Run QAService checks against workspace files in a live Docker sandbox.

    Verifies:
    1. QAService operates against real Docker sandbox filesystem boundary.
    2. HTML validation, broken links, build, and console checks execute.
    3. Aggregates into domain QAReport and machine-readable JSON.
    4. Sandbox container is safely destroyed on completion.
    """
    import docker

    client = docker.from_env()
    config = SandboxConfig(
        image="agency-sandbox:latest",
        base_workspace_dir=tmp_path / "qa_docker_workspaces",
        command_timeout=60,
    )
    sandbox = DockerSandbox(client=client, config=config)
    sandbox_id = sandbox.create("agency-sandbox:latest")

    try:
        # Populate realistic HTML output files inside container workspace
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Portfolio - Home</title>
</head>
<body>
    <header>
        <nav>
            <a href="/about/">About</a>
            <a href="/projects/">Projects</a>
            <a href="/contact/">Contact</a>
        </nav>
    </header>
    <main>
        <h1>Welcome to My Agency Portfolio</h1>
        <p>Expert software delivery.</p>
    </main>
</body>
</html>"""
        about_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Portfolio - About</title>
</head>
<body>
    <header><nav><a href="/">Home</a></nav></header>
    <main>
        <h1>About Our Team</h1>
        <p>Decades of engineering leadership.</p>
    </main>
</body>
</html>"""
        projects_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Portfolio - Projects</title>
</head>
<body>
    <header><nav><a href="/">Home</a></nav></header>
    <main>
        <h1>Featured Projects</h1>
        <p>Enterprise applications built with discipline.</p>
    </main>
</body>
</html>"""
        contact_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Portfolio - Contact</title>
</head>
<body>
    <header><nav><a href="/">Home</a></nav></header>
    <main>
        <h1>Contact Us</h1>
        <p>Get in touch today.</p>
    </main>
</body>
</html>"""

        # Write generated site into dist/ inside sandbox
        sandbox.write_file(sandbox_id, "dist/index.html", index_html)
        sandbox.write_file(sandbox_id, "dist/about/index.html", about_html)
        sandbox.write_file(sandbox_id, "dist/projects/index.html", projects_html)
        sandbox.write_file(sandbox_id, "dist/contact/index.html", contact_html)

        # Write mock QA reports (axe, lighthouse, browser console)
        axe_report = json.dumps([])
        sandbox.write_file(sandbox_id, "axe-report.json", axe_report)

        qa_report_data = {
            "console_errors": {"passed": True},
            "lighthouse": {
                "performance": 95,
                "accessibility": 95,
                "best_practices": 95,
                "seo": 95,
            },
        }
        sandbox.write_file(sandbox_id, "qa-report.json", json.dumps(qa_report_data))

        build_res = BuildResult(
            workspace_path="/workspace",
            commit_sha="a" * 40,
            build_ok=True,
            logs="Build succeeded",
        )

        context = QAContext(
            run_id="docker-qa-run",
            sandbox=sandbox,
            sandbox_id=sandbox_id,
            build_result=build_res,
            artifacts=["index.html"],
            routes=["/", "/about/", "/projects/", "/contact/"],
            lighthouse_scores={
                "performance": 95,
                "accessibility": 95,
                "best_practices": 95,
                "seo": 95,
            },
        )

        service = QAService()
        report, results, build_agent_json = service.run_with_details(context)

        # Verify results
        assert isinstance(report, QAReport)
        assert len(results) == 6
        assert all(isinstance(r, CheckResult) for r in results)
        assert all(r.status == CheckStatus.PASSED for r in results)
        assert report.overall_passed is True

        # Verify build agent JSON output
        parsed_json = json.loads(build_agent_json)
        assert parsed_json["run_id"] == "docker-qa-run"
        assert parsed_json["overall_passed"] is True
        assert len(parsed_json["checks"]) == 6

    finally:
        sandbox.destroy(sandbox_id)
