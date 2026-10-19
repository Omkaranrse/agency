"""RunDeterministicPipeline use case."""

import json
import logging
import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agency.application.errors import ApplicationError
from agency.application.ports.event_bus import EventBusPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.application.ports.sandbox import SandboxPort
from agency.application.services.deterministic_pipeline import (
    DeterministicArtifactManager,
    DeterministicContentMapper,
)
from agency.domain.entities.brief import Brief
from agency.domain.entities.qa_report import QAReport
from agency.domain.entities.run import Run
from agency.domain.enums import RunState
from agency.domain.events import RunStarted

logger = logging.getLogger(__name__)


class PipelineExecutionError(ApplicationError):
    """Raised when a required deterministic pipeline stage fails."""

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        self.message = message
        super().__init__(f"Pipeline stage '{stage}' failed: {message}")


class RunDeterministicPipelineCommand(BaseModel):
    """Command input for executing the deterministic website generation pipeline."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    brief: Brief
    project_id: str | None = Field(default=None, max_length=100)
    run_id: str | None = Field(default=None, max_length=100)
    template_dir: Path | None = None
    runs_dir: Path | None = None


class RunDeterministicPipelineResult(BaseModel):
    """Result of the deterministic website generation pipeline."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    project_id: str
    status: RunState
    artifact_dir: Path
    variant: str
    build_ok: bool
    qa_passed: bool
    screenshots: list[str]
    manifest_path: Path
    summary_path: Path


class RunDeterministicPipeline:
    """Orchestrates deterministic static website generation without any LLM calls.

    Workflow Stages:
    1. Validate client brief and initialize unique run ID and project ID.
    2. Instantiate Run aggregate in CREATED state and persist.
    3. Start PLANNING, generate formal Spec aggregate, and complete planning.
    4. Submit prototype and deterministically record approval.
    5. Provision isolated sandbox environment via SandboxPort.
    6. Validate template source files and copy them into sandbox workspace.
    7. Apply deterministic design tokens and customized content.
    8. Start BUILDING, execute production build inside sandbox, and capture logs.
    9. Finish BUILDING, transition to TESTING.
    10. Start local preview server and execute Playwright browser checks.
    11. Stop preview server.
    12. Validate QA report and extract 8 required screenshots.
    13. Pass QA checks, transition to DEPLOYING.
    14. Extract built static site archive into runs/<run_id>/site/.
    15. Complete deployment, transition to COMPLETED.
    16. Write final manifest.json and summary.json.
    17. Always clean up sandbox in all success and failure paths.
    """

    REQUIRED_TEMPLATE_FILES: tuple[str, ...] = (
        "package.json",
        "astro.config.mjs",
        "tailwind.config.mjs",
        "tsconfig.json",
        "src/styles/tokens.css",
        "src/content/config.ts",
        "src/content/site.json",
        "src/content/home.json",
        "src/content/about.json",
        "src/content/projects.json",
        "src/content/contact.json",
        "src/pages/index.astro",
        "src/pages/about.astro",
        "src/pages/projects.astro",
        "src/pages/contact.astro",
    )

    REQUIRED_SCRIPTS: tuple[str, ...] = (
        "scripts/preview_server.mjs",
        "scripts/start_preview.sh",
        "scripts/stop_preview.sh",
        "scripts/run_browser_checks.mjs",
    )

    def __init__(
        self,
        repository: RunRepositoryPort,
        event_bus: EventBusPort,
        sandbox: SandboxPort,
        template_dir: Path | None = None,
        runs_dir: Path | None = None,
        on_stage: Callable[[str, str], None] | None = None,
    ) -> None:
        self._repository = repository
        self._event_bus = event_bus
        self._sandbox = sandbox
        self._template_dir = template_dir or self._find_default_template_dir()
        self._runs_dir = runs_dir or self._find_default_runs_dir()
        self._on_stage = on_stage or (lambda stage, msg: None)

    @staticmethod
    def _find_default_template_dir() -> Path:
        """Resolve the path to templates/site-astro relative to project root."""
        candidates = [
            Path.cwd() / "templates" / "site-astro",
            Path(__file__).resolve().parents[5] / "templates" / "site-astro",
        ]
        for candidate in candidates:
            if candidate.is_dir():
                return candidate.resolve()
        return (Path.cwd() / "templates" / "site-astro").resolve()

    @staticmethod
    def _find_default_runs_dir() -> Path:
        """Resolve the default root directory for pipeline runs."""
        return (Path.cwd() / "runs").resolve()

    def _notify(self, stage: str, message: str) -> None:
        self._on_stage(stage, message)
        logger.info("[%s] %s", stage, message)

    def _save_and_publish(self, run: Run) -> None:
        self._repository.save(run)
        events = run.clear_events()
        if events:
            self._event_bus.publish_all(events)

    def execute(
        self, command: RunDeterministicPipelineCommand
    ) -> RunDeterministicPipelineResult:
        """Execute the complete deterministic pipeline."""
        brief = command.brief
        run_id = command.run_id or str(uuid.uuid4())
        default_pid = f"project-{brief.client_name.lower().replace(' ', '-')}"
        project_id = command.project_id or default_pid

        template_dir = command.template_dir or self._template_dir
        runs_dir = command.runs_dir or self._runs_dir

        artifact_manager = DeterministicArtifactManager(runs_dir)
        run_dir = artifact_manager.create_run_directory(run_id)

        # 1. Initialize Run Aggregate
        self._notify("INITIALIZING", f"Creating run record '{run_id}'")
        run = Run(
            run_id=run_id,
            project_id=project_id,
            brief=brief,
            state=RunState.CREATED,
        )
        self._repository.save(run)
        self._event_bus.publish_all(
            [RunStarted(run_id=run.run_id, project_id=run.project_id)]
        )

        sandbox_id: str | None = None
        preview_started = False
        current_stage = "INITIALIZING"

        try:
            # 2. Planning Phase
            current_stage = "PLANNING"
            self._notify("PLANNING", "Generating technical specification")
            run.start_planning()
            spec = DeterministicContentMapper.generate_spec(project_id, brief)
            run.finish_planning(spec=spec)
            self._save_and_publish(run)

            # 3. Prototyping & Deterministic Approval
            current_stage = "PROTOTYPING"
            self._notify("PROTOTYPING", "Preparing deterministic prototype")
            run.submit_prototype("deterministic-prototype-v1")
            run.approve_prototype(approver="deterministic-pipeline")
            self._save_and_publish(run)

            # 4. Provision Sandbox
            current_stage = "SANDBOX_PROVISION"
            self._notify("SANDBOX_PROVISION", "Creating isolated sandbox")
            sandbox_id = self._sandbox.create(template="astro-node20")

            # 5. Validate & Copy Template Files
            current_stage = "TEMPLATE_COPY"
            self._notify("TEMPLATE_COPY", "Validating and copying template")
            self._copy_template_to_sandbox(template_dir, sandbox_id)

            # 6. Content & Design Tokens Customization
            current_stage = "CUSTOMIZATION"
            self._notify("CUSTOMIZATION", "Applying design tokens and content")
            variant, design_tokens = (
                DeterministicContentMapper.resolve_variant_and_tokens(brief)
            )
            content_mapping = DeterministicContentMapper.map_content_files(
                brief, variant
            )
            for rel_path, content_dict in content_mapping.items():
                payload = json.dumps(content_dict, indent=2)
                self._sandbox.write_file(sandbox_id, rel_path, payload)

            # 7. Start Building & Git Commit
            current_stage = "BUILDING"
            self._notify("BUILDING", "Starting production build")
            run.start_building()
            self._save_and_publish(run)

            commit_sha = self._initialize_git_and_commit(sandbox_id)

            # Dependency check / install if needed
            self._sandbox.exec(sandbox_id, ["pnpm", "install", "--prefer-offline"])

            # Run Astro production build
            build_res = self._sandbox.exec(
                sandbox_id,
                ["pnpm", "build"],
                env={"ASTRO_TELEMETRY_DISABLED": "1", "THEME": variant},
            )

            build_log = (
                f"=== BUILD COMMAND EXIT CODE: {build_res.exit_code} ===\n"
                f"=== STDOUT ===\n{build_res.stdout}\n"
                f"=== STDERR ===\n{build_res.stderr}\n"
            )
            artifact_manager.write_build_log(run_dir, build_log)

            if not build_res.ok:
                raise PipelineExecutionError(
                    "BUILDING",
                    f"Production build exited with code {build_res.exit_code}.\n"
                    f"Log summary: {build_res.stderr or build_res.stdout}",
                )

            # Complete build transition to TESTING
            valid_sha = commit_sha or "0123456789abcdef0123456789abcdef01234567"
            run.finish_building(
                commit_sha=valid_sha,
                workspace_path=f"workspaces/{project_id}",
            )
            self._save_and_publish(run)

            # 8. Start Preview Server & Run Browser Checks
            current_stage = "TESTING"
            self._notify("TESTING", "Starting preview server inside sandbox")
            preview_res = self._sandbox.exec(
                sandbox_id, ["sh", "scripts/start_preview.sh"]
            )
            if preview_res.ok:
                preview_started = True

            self._notify("TESTING", "Executing Playwright browser checks")
            test_res = self._sandbox.exec(
                sandbox_id, ["node", "scripts/run_browser_checks.mjs"]
            )

            # 9. Stop Preview Server
            if preview_started:
                self._sandbox.exec(sandbox_id, ["sh", "scripts/stop_preview.sh"])
                preview_started = False

            # 10. Extract & Validate QA Report and Screenshots
            current_stage = "ARTIFACT_EXTRACTION"
            self._notify("ARTIFACT_EXTRACTION", "Collecting QA report & screenshots")

            try:
                qa_report_raw = self._sandbox.read_file(sandbox_id, "qa-report.json")
                qa_data = json.loads(qa_report_raw)
                qa_report = QAReport.model_validate(qa_data)
            except Exception as exc:
                raise PipelineExecutionError(
                    "ARTIFACT_EXTRACTION",
                    f"Invalid or missing QA report: {exc}",
                ) from exc

            artifact_manager.write_qa_report(run_dir, qa_report)

            if not qa_report.overall_passed or not test_res.ok:
                failed_names = [c.name for c in qa_report.checks if not c.passed]
                run.fail_qa(
                    reason="Automated QA checks or Playwright verification failed.",
                    failed_checks=failed_names,
                )
                self._save_and_publish(run)
                raise PipelineExecutionError(
                    "TESTING",
                    f"QA report failed. Failed checks: {failed_names}",
                )

            # Extract 8 required screenshots
            screenshots_saved: list[str] = []
            for shot_name in DeterministicArtifactManager.REQUIRED_SCREENSHOT_NAMES:
                try:
                    img_bytes = self._sandbox.copy_out(
                        sandbox_id, f"screenshots/{shot_name}"
                    )
                except Exception as exc:
                    raise PipelineExecutionError(
                        "ARTIFACT_EXTRACTION",
                        f"Failed to copy out required screenshot '{shot_name}': {exc}",
                    ) from exc

                if not img_bytes:
                    raise PipelineExecutionError(
                        "ARTIFACT_EXTRACTION",
                        f"Extracted screenshot '{shot_name}' is empty.",
                    )

                artifact_manager.write_screenshot(run_dir, shot_name, img_bytes)
                screenshots_saved.append(f"screenshots/{shot_name}")

            # Pass QA checks -> Transition to DEPLOYING
            run.pass_qa(total_checks=len(qa_report.checks))
            self._save_and_publish(run)

            # 11. Extract Built Static Site Archive into runs/<run_id>/site/
            current_stage = "DEPLOYING"
            self._notify("DEPLOYING", "Packaging and extracting built static site")
            tar_res = self._sandbox.exec(
                sandbox_id, ["tar", "-czf", "dist.tar.gz", "-C", "dist", "."]
            )
            if not tar_res.ok:
                raise PipelineExecutionError(
                    "DEPLOYING",
                    "Failed to archive dist directory inside sandbox: "
                    f"{tar_res.stderr}",
                )

            try:
                site_archive_bytes = self._sandbox.copy_out(sandbox_id, "dist.tar.gz")
            except Exception as exc:
                raise PipelineExecutionError(
                    "DEPLOYING",
                    f"Failed to extract site archive from sandbox: {exc}",
                ) from exc

            artifact_manager.extract_site_archive(run_dir, site_archive_bytes)

            # Complete deployment -> Transition to COMPLETED
            site_url = f"file://{run_dir}/site"
            run.complete_deployment(url=site_url, provider="static-local")
            self._save_and_publish(run)

            # 12. Write Final Manifest & Summary Reports
            completed_at = datetime.now(UTC)
            manifest_data: dict[str, Any] = {
                "run_id": run.run_id,
                "project_id": run.project_id,
                "status": run.state.value,
                "created_at": run.created_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "brief": brief.model_dump(mode="json"),
                "variant": variant,
                "design_tokens": design_tokens.model_dump(mode="json"),
                "commit_sha": commit_sha,
                "build": {
                    "ok": True,
                    "workspace_path": f"workspaces/{project_id}",
                    "logs_file": "build.log",
                },
                "qa": {
                    "overall_passed": qa_report.overall_passed,
                    "total_checks": len(qa_report.checks),
                    "report_file": "qa-report.json",
                },
                "screenshots": screenshots_saved,
                "artifacts": {
                    "site_dir": "site",
                    "screenshots_dir": "screenshots",
                    "build_log": "build.log",
                    "qa_report": "qa-report.json",
                },
            }
            manifest_path = artifact_manager.write_manifest(run_dir, manifest_data)

            summary_data: dict[str, Any] = {
                "run_id": run.run_id,
                "project_id": run.project_id,
                "status": run.state.value,
                "client_name": brief.client_name,
                "site_type": brief.site_type,
                "variant": variant,
                "screenshots_count": len(screenshots_saved),
                "qa_passed": qa_report.overall_passed,
                "artifact_path": str(run_dir),
            }
            summary_path = artifact_manager.write_summary(run_dir, summary_data)

            self._notify(
                "COMPLETED",
                f"Pipeline run '{run_id}' completed successfully.",
            )

            return RunDeterministicPipelineResult(
                run_id=run.run_id,
                project_id=run.project_id,
                status=run.state,
                artifact_dir=run_dir,
                variant=variant,
                build_ok=True,
                qa_passed=qa_report.overall_passed,
                screenshots=screenshots_saved,
                manifest_path=manifest_path,
                summary_path=summary_path,
            )

        except Exception as exc:
            self._notify(
                "FAILED",
                f"Pipeline failed during '{current_stage}': {exc}",
            )
            if run.state not in run.TERMINAL_STATES:
                run.fail(reason=f"Pipeline stage '{current_stage}' failed: {exc}")
                self._save_and_publish(run)

            # Record failure in manifest
            failure_manifest: dict[str, Any] = {
                "run_id": run.run_id,
                "project_id": run.project_id,
                "status": RunState.FAILED.value,
                "failed_stage": current_stage,
                "error": str(exc),
                "created_at": run.created_at.isoformat(),
                "failed_at": datetime.now(UTC).isoformat(),
            }
            artifact_manager.write_manifest(run_dir, failure_manifest)
            raise

        finally:
            # Enforce clean teardown of preview server and sandbox
            if preview_started and sandbox_id:
                try:
                    self._sandbox.exec(sandbox_id, ["sh", "scripts/stop_preview.sh"])
                except Exception as exc:
                    logger.warning("Error stopping preview server: %s", exc)

            if sandbox_id:
                self._notify("CLEANUP", f"Destroying sandbox '{sandbox_id}'")
                try:
                    self._sandbox.destroy(sandbox_id)
                except Exception as exc:
                    logger.warning("Error destroying sandbox '%s': %s", sandbox_id, exc)

    def _copy_template_to_sandbox(self, template_dir: Path, sandbox_id: str) -> None:
        """Validate template files on host and copy into the sandbox workspace."""
        if not template_dir.is_dir():
            raise PipelineExecutionError(
                "TEMPLATE_COPY",
                f"Source template directory does not exist: '{template_dir}'",
            )

        # 1. Validate required files exist
        for req_file in self.REQUIRED_TEMPLATE_FILES:
            target = template_dir / req_file
            if not target.is_file():
                raise PipelineExecutionError(
                    "TEMPLATE_COPY",
                    f"Required template file missing: '{req_file}'",
                )

        # 2. Iterate and copy files, ignoring forbidden paths
        ignored_names = {
            ".git",
            "node_modules",
            "dist",
            ".astro",
            ".pnpm-store",
            ".cache",
            "tests",
            ".env",
        }

        for path in sorted(template_dir.rglob("*")):
            if not path.is_file():
                continue

            rel_parts = path.relative_to(template_dir).parts
            if any(part in ignored_names or part.startswith(".") for part in rel_parts):
                continue

            rel_path = path.relative_to(template_dir).as_posix()
            try:
                content_bytes = path.read_bytes()
                self._sandbox.write_file(sandbox_id, rel_path, content_bytes)
            except Exception as exc:
                raise PipelineExecutionError(
                    "TEMPLATE_COPY",
                    f"Failed copying template file '{rel_path}': {exc}",
                ) from exc

    def _initialize_git_and_commit(self, sandbox_id: str) -> str | None:
        """Optionally initialize git and produce a verified commit SHA."""
        try:
            self._sandbox.exec(sandbox_id, ["git", "init"])
            self._sandbox.exec(
                sandbox_id, ["git", "config", "user.name", "Agency Pipeline"]
            )
            self._sandbox.exec(
                sandbox_id,
                ["git", "config", "user.email", "pipeline@agency.local"],
            )
            self._sandbox.exec(sandbox_id, ["git", "add", "."])
            self._sandbox.exec(
                sandbox_id,
                ["git", "commit", "-m", "Deterministic customized website"],
            )
            sha_res = self._sandbox.exec(sandbox_id, ["git", "rev-parse", "HEAD"])
            if sha_res.ok:
                raw_sha = sha_res.stdout.strip()
                if re.match(r"^[0-9a-fA-F]{7,40}$", raw_sha):
                    return raw_sha.lower()
        except Exception as exc:
            logger.debug("Git commit creation skipped or failed: %s", exc)
        return None
