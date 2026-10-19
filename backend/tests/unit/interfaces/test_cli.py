"""Unit tests for the Agency CLI interface."""

import json
from pathlib import Path

import pytest
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_run_repository import FakeRunRepository
from tests.unit.application.test_deterministic_pipeline import (
    PipelineFakeSandbox,
)

from agency.domain.enums import RunState
from agency.interfaces.cli.main import main


@pytest.fixture
def valid_brief_path(tmp_path: Path) -> Path:
    """Create a temporary valid brief.json file."""
    brief_data = {
        "client_name": "Devon Miller",
        "site_type": "Portfolio",
        "pages": ["Home", "About", "Projects", "Contact"],
        "tone": "editorial",
        "content_notes": "Senior staff engineer portfolio.",
        "links": ["https://github.com/devonmiller"],
    }
    path = tmp_path / "brief.json"
    path.write_text(json.dumps(brief_data), encoding="utf-8")
    return path


@pytest.fixture
def valid_template_dir() -> Path:
    """Return path to templates/site-astro."""
    return Path(__file__).resolve().parents[4] / "templates" / "site-astro"


def test_cli_help(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify that --help exits with 0 and prints usage."""
    code = main(["--help"])
    assert code == 0
    captured = capsys.readouterr()
    assert "agency" in captured.out
    assert "Available commands" in captured.out


def test_cli_run_help(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify that run --help exits with 0 and prints arguments."""
    code = main(["run", "--help"])
    assert code == 0
    captured = capsys.readouterr()
    assert "--no-llm" in captured.out
    assert "brief" in captured.out


def test_cli_run_missing_no_llm_flag(
    valid_brief_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify that omitting --no-llm flag causes a failure with actionable message."""
    code = main(["run", str(valid_brief_path)])
    assert code == 1
    captured = capsys.readouterr()
    assert "Phase 5 only supports deterministic pipeline execution" in captured.err
    assert "--no-llm" in captured.err


def test_cli_run_non_existent_brief(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify that passing a non-existent brief file exits with code 1."""
    missing = tmp_path / "does_not_exist.json"
    code = main(["run", str(missing), "--no-llm"])
    assert code == 1
    captured = capsys.readouterr()
    assert "Brief file not found" in captured.err


def test_cli_run_malformed_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify that passing a malformed JSON file exits with code 1."""
    malformed = tmp_path / "bad.json"
    malformed.write_text("{ unquoted_key: 123 ", encoding="utf-8")

    code = main(["run", str(malformed), "--no-llm"])
    assert code == 1
    captured = capsys.readouterr()
    assert "malformed JSON" in captured.err


def test_cli_run_invalid_brief_schema(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify that passing an invalid brief schema exits with code 1."""
    invalid_data = {
        "client_name": "",  # Empty client name
        "site_type": "Portfolio",
        "pages": [],  # Empty pages
        "tone": "editorial",
        "content_notes": "Note",
    }
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(invalid_data), encoding="utf-8")

    code = main(["run", str(path), "--no-llm"])
    assert code == 1
    captured = capsys.readouterr()
    assert "failed validation" in captured.err
    assert "client_name" in captured.err


def test_cli_run_success_e2e(
    valid_brief_path: Path,
    valid_template_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify full CLI execution using injected in-memory fake adapters."""
    repo = FakeRunRepository()
    bus = FakeEventBus()
    sandbox = PipelineFakeSandbox(auto_populate=True)
    runs_dir = tmp_path / "runs"

    code = main(
        argv=[
            "run",
            str(valid_brief_path),
            "--no-llm",
            "--template-dir",
            str(valid_template_dir),
            "--runs-dir",
            str(runs_dir),
        ],
        repository=repo,
        event_bus=bus,
        sandbox=sandbox,
    )
    assert code == 0

    captured = capsys.readouterr()
    assert "AGENCY PIPELINE COMPLETED SUCCESSFULLY" in captured.out
    assert "Screenshots:  8/8 captured" in captured.out
    assert "Variant:      editorial" in captured.out
    assert str(runs_dir) in captured.out

    # Verify repository state
    runs = repo.list()
    assert len(runs) == 1
    assert runs[0].state == RunState.COMPLETED


def test_cli_run_pipeline_failure(
    valid_brief_path: Path,
    valid_template_dir: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify CLI error reporting when pipeline encounters build error."""
    repo = FakeRunRepository()
    bus = FakeEventBus()
    sandbox = PipelineFakeSandbox(auto_populate=False)
    # When auto_populate is False, QA report will be missing
    runs_dir = tmp_path / "runs"

    code = main(
        argv=[
            "run",
            str(valid_brief_path),
            "--no-llm",
            "--template-dir",
            str(valid_template_dir),
            "--runs-dir",
            str(runs_dir),
        ],
        repository=repo,
        event_bus=bus,
        sandbox=sandbox,
    )
    assert code == 1
    captured = capsys.readouterr()
    assert "FAILED" in captured.err
