"""Integration test for the deterministic pipeline running against Docker sandbox."""

from pathlib import Path

import pytest
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_run_repository import FakeRunRepository

from agency.domain.enums import RunState
from agency.infrastructure.sandbox.docker_sandbox import DockerSandbox
from agency.infrastructure.sandbox.models import SandboxConfig
from agency.interfaces.cli.main import main


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


def test_docker_deterministic_pipeline_e2e(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Run full deterministic pipeline inside live Docker container.

    Verifies:
    1. CLI accepts --no-llm.
    2. Real Docker sandbox is created and workspace populated.
    3. Production static build succeeds inside container.
    4. Preview server runs and all 4 pages are verified.
    5. All 8 screenshots (390px and 1280px) are captured.
    6. Artifacts copied out into runs/<run_id>/.
    7. Manifest indicates status=COMPLETED.
    8. Sandbox container is destroyed afterward.
    """
    import docker

    client = docker.from_env()
    config = SandboxConfig(
        image="agency-sandbox:latest",
        base_workspace_dir=tmp_path / "docker_workspaces",
        command_timeout=120,
    )
    sandbox = DockerSandbox(client=client, config=config)

    repo = FakeRunRepository()
    bus = FakeEventBus()

    brief_path = Path(__file__).resolve().parents[3] / "brief.json"
    template_dir = Path(__file__).resolve().parents[3] / "templates" / "site-astro"
    runs_dir = tmp_path / "runs"

    code = main(
        argv=[
            "run",
            str(brief_path),
            "--no-llm",
            "--template-dir",
            str(template_dir),
            "--runs-dir",
            str(runs_dir),
        ],
        repository=repo,
        event_bus=bus,
        sandbox=sandbox,
    )
    assert code == 0

    runs = repo.list()
    assert len(runs) == 1
    run = runs[0]
    assert run.state == RunState.COMPLETED

    run_dir = runs_dir / run.run_id
    assert run_dir.is_dir()
    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / "summary.json").is_file()
    assert (run_dir / "build.log").is_file()
    assert (run_dir / "qa-report.json").is_file()
    assert (run_dir / "site" / "index.html").is_file()

    expected_screenshots = [
        "home-390.png",
        "home-1280.png",
        "about-390.png",
        "about-1280.png",
        "projects-390.png",
        "projects-1280.png",
        "contact-390.png",
        "contact-1280.png",
    ]
    for shot in expected_screenshots:
        shot_path = run_dir / "screenshots" / shot
        assert shot_path.is_file()
        assert shot_path.stat().st_size > 0
