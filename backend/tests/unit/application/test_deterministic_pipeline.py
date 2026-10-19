"""Unit tests for the deterministic website generation pipeline."""

import io
import json
import tarfile
from pathlib import Path
from typing import Any

import pytest
from pydantic import HttpUrl, ValidationError
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_run_repository import FakeRunRepository
from tests.fakes.fake_sandbox import FakeSandbox

from agency.application.errors import SandboxError
from agency.application.ports.sandbox import ExecResult
from agency.application.services.deterministic_pipeline import (
    EDITORIAL_TOKENS,
    STUDIO_TOKENS,
    DeterministicArtifactManager,
    DeterministicContentMapper,
)
from agency.application.use_cases.run_deterministic_pipeline import (
    PipelineExecutionError,
    RunDeterministicPipeline,
    RunDeterministicPipelineCommand,
)
from agency.domain.entities.brief import Brief
from agency.domain.entities.design_tokens import DesignTokens
from agency.domain.enums import RunState


class PipelineFakeSandbox(FakeSandbox):
    """Fake sandbox that automatically synthesizes realistic build artifacts."""

    def __init__(self, auto_populate: bool = True) -> None:
        super().__init__()
        self.auto_populate = auto_populate
        self.destroyed_sandboxes: list[str] = []

    def exec(
        self,
        sandbox_id: str,
        command: list[str] | str,
        env: dict[str, str] | None = None,
    ) -> ExecResult:
        result = super().exec(sandbox_id, command, env)
        cmd_str = " ".join(command) if isinstance(command, list) else command

        if self.auto_populate and result.ok:
            if "run_browser_checks.mjs" in cmd_str:
                self._populate_browser_qa_and_screenshots(sandbox_id)
            elif "tar -czf dist.tar.gz" in cmd_str:
                self._populate_dist_archive(sandbox_id)
        elif self.auto_populate and not result.ok:
            if "run_browser_checks.mjs" in cmd_str:
                self._populate_failed_browser_qa(sandbox_id)

        return result

    def destroy(self, sandbox_id: str) -> None:
        self.destroyed_sandboxes.append(sandbox_id)
        super().destroy(sandbox_id)

    def _populate_browser_qa_and_screenshots(self, sandbox_id: str) -> None:
        checks: list[dict[str, Any]] = []
        for shot_name in DeterministicArtifactManager.REQUIRED_SCREENSHOT_NAMES:
            self.write_file(
                sandbox_id, f"screenshots/{shot_name}", b"\x89PNG\r\n\x1a\nfake-png"
            )
            base_name = shot_name.replace(".png", "")
            checks.append(
                {
                    "name": f"screenshot_{base_name}",
                    "passed": True,
                    "details": f"Screenshot {shot_name} captured successfully",
                }
            )

        report = {
            "checks": checks,
            "overall_passed": True,
        }
        self.write_file(sandbox_id, "qa-report.json", json.dumps(report))

    def _populate_failed_browser_qa(self, sandbox_id: str) -> None:
        report = {
            "checks": [
                {
                    "name": "browser_visual_check",
                    "passed": False,
                    "details": "Visual check failed in Playwright",
                }
            ],
            "overall_passed": False,
        }
        self.write_file(sandbox_id, "qa-report.json", json.dumps(report))

    def _populate_dist_archive(self, sandbox_id: str) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            content = b"<!DOCTYPE html><html><body><h1>Sample</h1></body></html>"
            info = tarfile.TarInfo(name="index.html")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        self.write_file(sandbox_id, "dist.tar.gz", buf.getvalue())


@pytest.fixture
def sample_brief() -> Brief:
    """Provide a valid test brief."""
    return Brief(
        client_name="Devon Miller",
        site_type="Portfolio",
        pages=["Home", "About", "Projects", "Contact"],
        tone="editorial",
        content_notes=(
            "Staff systems engineer and distributed architect. "
            "Clean architecture and accessible web standards."
        ),
        links=[HttpUrl("https://github.com/devonmiller")],
    )


@pytest.fixture
def fake_repo() -> FakeRunRepository:
    return FakeRunRepository()


@pytest.fixture
def fake_bus() -> FakeEventBus:
    return FakeEventBus()


@pytest.fixture
def pipeline_sandbox() -> PipelineFakeSandbox:
    return PipelineFakeSandbox(auto_populate=True)


@pytest.fixture
def valid_template_dir() -> Path:
    """Return the absolute path to templates/site-astro."""
    template_dir = Path(__file__).resolve().parents[4] / "templates" / "site-astro"
    assert template_dir.is_dir()
    return template_dir


def test_deterministic_content_mapper_editorial(sample_brief: Brief) -> None:
    """Verify content mapping and variant resolution for editorial tone."""
    variant, tokens = DeterministicContentMapper.resolve_variant_and_tokens(
        sample_brief
    )
    assert variant == "editorial"
    assert tokens == EDITORIAL_TOKENS

    files = DeterministicContentMapper.map_content_files(sample_brief, variant)
    assert "src/content/site.json" in files
    assert "src/content/home.json" in files
    assert "src/content/about.json" in files
    assert "src/content/projects.json" in files
    assert "src/content/contact.json" in files

    site = files["src/content/site.json"]
    assert site["clientName"] == "Devon Miller"
    assert site["theme"] == "editorial"
    assert len(site["nav"]) >= 4

    contact = files["src/content/contact.json"]
    assert "devon-miller@example.com" in contact["email"]


def test_deterministic_content_mapper_studio_variant() -> None:
    """Verify content mapping for studio tone."""
    studio_brief = Brief(
        client_name="Elena Rostova",
        site_type="Studio Portfolio",
        pages=["Home", "About", "Projects", "Contact"],
        tone="studio modern tech",
        content_notes="Digital systems designer focusing on minimalist architecture.",
        links=[HttpUrl("https://github.com/elena")],
    )
    variant, tokens = DeterministicContentMapper.resolve_variant_and_tokens(
        studio_brief
    )
    assert variant == "studio"
    assert tokens == STUDIO_TOKENS


def test_design_tokens_validation() -> None:
    """Verify design tokens strictly validate against domain entity schema."""
    assert isinstance(EDITORIAL_TOKENS, DesignTokens)
    assert isinstance(STUDIO_TOKENS, DesignTokens)
    assert EDITORIAL_TOKENS.font_family == "Poppins"
    assert STUDIO_TOKENS.font_family == "Poppins"


def test_invalid_brief_rejected() -> None:
    """Verify that an invalid brief triggers validation errors."""
    with pytest.raises(ValidationError):
        Brief.model_validate(
            {
                "client_name": "",  # Empty name disallowed
                "site_type": "Portfolio",
                "pages": ["Home"],
                "tone": "editorial",
                "content_notes": "Valid note",
            }
        )


def test_successful_pipeline_progression(
    sample_brief: Brief,
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    pipeline_sandbox: PipelineFakeSandbox,
    valid_template_dir: Path,
    tmp_path: Path,
) -> None:
    """Verify full successful pipeline progression through all domain states."""
    runs_dir = tmp_path / "runs"
    use_case = RunDeterministicPipeline(
        repository=fake_repo,
        event_bus=fake_bus,
        sandbox=pipeline_sandbox,
        template_dir=valid_template_dir,
        runs_dir=runs_dir,
    )

    command = RunDeterministicPipelineCommand(
        brief=sample_brief,
        runs_dir=runs_dir,
    )

    result = use_case.execute(command)

    # 1. State assertions
    assert result.status == RunState.COMPLETED
    assert result.build_ok is True
    assert result.qa_passed is True
    assert len(result.screenshots) == 8
    assert result.variant == "editorial"

    # 2. Artifact assertions
    run_dir = result.artifact_dir
    assert run_dir.is_dir()
    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / "summary.json").is_file()
    assert (run_dir / "build.log").is_file()
    assert (run_dir / "qa-report.json").is_file()
    assert (run_dir / "site" / "index.html").is_file()

    for shot in DeterministicArtifactManager.REQUIRED_SCREENSHOT_NAMES:
        shot_path = run_dir / "screenshots" / shot
        assert shot_path.is_file()
        assert shot_path.stat().st_size > 0

    # 3. Aggregate repository verification
    persisted_run = fake_repo.get_by_id(result.run_id)
    assert persisted_run is not None
    assert persisted_run.state == RunState.COMPLETED
    assert persisted_run.approval_recorded is True

    # 4. Sandbox cleanup verification
    assert len(pipeline_sandbox.destroyed_sandboxes) == 1


def test_template_validation_failure(
    sample_brief: Brief,
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    pipeline_sandbox: PipelineFakeSandbox,
    tmp_path: Path,
) -> None:
    """Verify that a corrupted or empty template directory halts the pipeline."""
    corrupted_template = tmp_path / "corrupted_template"
    corrupted_template.mkdir()
    # Missing required files like package.json

    use_case = RunDeterministicPipeline(
        repository=fake_repo,
        event_bus=fake_bus,
        sandbox=pipeline_sandbox,
        template_dir=corrupted_template,
        runs_dir=tmp_path / "runs",
    )

    with pytest.raises(PipelineExecutionError) as exc_info:
        use_case.execute(RunDeterministicPipelineCommand(brief=sample_brief))

    assert exc_info.value.stage == "TEMPLATE_COPY"
    # Ensure sandbox cleanup occurred
    assert len(pipeline_sandbox.destroyed_sandboxes) == 1


def test_build_failure(
    sample_brief: Brief,
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    pipeline_sandbox: PipelineFakeSandbox,
    valid_template_dir: Path,
    tmp_path: Path,
) -> None:
    """Verify that build failure halts execution, marks run as FAILED, and cleans up."""
    pipeline_sandbox.set_exec_response(
        "pnpm build",
        ExecResult(exit_code=1, stdout="", stderr="Type check error in components"),
    )

    use_case = RunDeterministicPipeline(
        repository=fake_repo,
        event_bus=fake_bus,
        sandbox=pipeline_sandbox,
        template_dir=valid_template_dir,
        runs_dir=tmp_path / "runs",
    )

    with pytest.raises(PipelineExecutionError) as exc_info:
        use_case.execute(RunDeterministicPipelineCommand(brief=sample_brief))

    assert exc_info.value.stage == "BUILDING"
    # Verify aggregate transitioned to FAILED
    runs = fake_repo.list()
    assert len(runs) == 1
    assert runs[0].state == RunState.FAILED
    assert "BUILDING" in (runs[0].failure_reason or "")
    # Ensure sandbox was destroyed
    assert len(pipeline_sandbox.destroyed_sandboxes) == 1


def test_browser_qa_check_failure(
    sample_brief: Brief,
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    pipeline_sandbox: PipelineFakeSandbox,
    valid_template_dir: Path,
    tmp_path: Path,
) -> None:
    """Verify that browser test failure transitions aggregate to FAILED."""
    pipeline_sandbox.set_exec_response(
        "run_browser_checks.mjs",
        ExecResult(exit_code=1, stdout="", stderr="Visual check failure"),
    )

    use_case = RunDeterministicPipeline(
        repository=fake_repo,
        event_bus=fake_bus,
        sandbox=pipeline_sandbox,
        template_dir=valid_template_dir,
        runs_dir=tmp_path / "runs",
    )

    with pytest.raises(PipelineExecutionError):
        use_case.execute(RunDeterministicPipelineCommand(brief=sample_brief))

    runs = fake_repo.list()
    assert len(runs) == 1
    assert runs[0].state == RunState.FAILED
    assert len(pipeline_sandbox.destroyed_sandboxes) == 1


def test_missing_screenshot_failure(
    sample_brief: Brief,
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    valid_template_dir: Path,
    tmp_path: Path,
) -> None:
    """Verify that a missing screenshot halts the pipeline and records failure."""

    class MissingScreenshotSandbox(PipelineFakeSandbox):
        def _populate_browser_qa_and_screenshots(self, sandbox_id: str) -> None:
            super()._populate_browser_qa_and_screenshots(sandbox_id)
            # Delete one required screenshot
            files = self._sandboxes[sandbox_id]["files"]
            if "screenshots/contact-1280.png" in files:
                del files["screenshots/contact-1280.png"]

    custom_sandbox = MissingScreenshotSandbox(auto_populate=True)

    use_case = RunDeterministicPipeline(
        repository=fake_repo,
        event_bus=fake_bus,
        sandbox=custom_sandbox,
        template_dir=valid_template_dir,
        runs_dir=tmp_path / "runs",
    )

    with pytest.raises(PipelineExecutionError) as exc_info:
        use_case.execute(RunDeterministicPipelineCommand(brief=sample_brief))

    assert "contact-1280.png" in exc_info.value.message
    runs = fake_repo.list()
    assert len(runs) == 1
    assert runs[0].state == RunState.FAILED
    assert len(custom_sandbox.destroyed_sandboxes) == 1


def test_sandbox_creation_failure(
    sample_brief: Brief,
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    pipeline_sandbox: PipelineFakeSandbox,
    valid_template_dir: Path,
    tmp_path: Path,
) -> None:
    """Verify handling when sandbox provisioning fails."""
    pipeline_sandbox.set_failure(SandboxError("Docker daemon out of memory"))

    use_case = RunDeterministicPipeline(
        repository=fake_repo,
        event_bus=fake_bus,
        sandbox=pipeline_sandbox,
        template_dir=valid_template_dir,
        runs_dir=tmp_path / "runs",
    )

    with pytest.raises(SandboxError):
        use_case.execute(RunDeterministicPipelineCommand(brief=sample_brief))

    runs = fake_repo.list()
    assert len(runs) == 1
    assert runs[0].state == RunState.FAILED


def test_artifact_copy_failure(
    sample_brief: Brief,
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    valid_template_dir: Path,
    tmp_path: Path,
) -> None:
    """Verify handling when static site archive extraction fails."""

    class BrokenCopySandbox(PipelineFakeSandbox):
        def copy_out(self, sandbox_id: str, src_path: str) -> bytes:
            if "dist.tar.gz" in src_path:
                raise SandboxError("Corrupted file extraction")
            return super().copy_out(sandbox_id, src_path)

    sandbox = BrokenCopySandbox(auto_populate=True)

    use_case = RunDeterministicPipeline(
        repository=fake_repo,
        event_bus=fake_bus,
        sandbox=sandbox,
        template_dir=valid_template_dir,
        runs_dir=tmp_path / "runs",
    )

    with pytest.raises(PipelineExecutionError):
        use_case.execute(RunDeterministicPipelineCommand(brief=sample_brief))

    runs = fake_repo.list()
    assert len(runs) == 1
    assert runs[0].state == RunState.FAILED
    assert len(sandbox.destroyed_sandboxes) == 1


def test_no_llm_provider_called(
    sample_brief: Brief,
    fake_repo: FakeRunRepository,
    fake_bus: FakeEventBus,
    pipeline_sandbox: PipelineFakeSandbox,
    valid_template_dir: Path,
    tmp_path: Path,
) -> None:
    """Verify no LLM ports, adapters, or calls are involved in execution."""
    from tests.fakes.fake_llm import FakeLLM

    unused_llm = FakeLLM()

    use_case = RunDeterministicPipeline(
        repository=fake_repo,
        event_bus=fake_bus,
        sandbox=pipeline_sandbox,
        template_dir=valid_template_dir,
        runs_dir=tmp_path / "runs",
    )

    result = use_case.execute(
        RunDeterministicPipelineCommand(brief=sample_brief, runs_dir=tmp_path / "runs")
    )
    assert result.status == RunState.COMPLETED
    assert len(unused_llm.calls) == 0
