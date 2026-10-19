"""CLI interface for Agency."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from agency.application.ports.event_bus import EventBusPort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.application.ports.sandbox import SandboxPort
from agency.application.use_cases.run_deterministic_pipeline import (
    PipelineExecutionError,
    RunDeterministicPipeline,
    RunDeterministicPipelineCommand,
)
from agency.domain.entities.brief import Brief


def _create_default_sandbox() -> SandboxPort:
    """Create a DockerSandbox instance using host Docker daemon."""
    try:
        import docker

        from agency.infrastructure.sandbox.docker_sandbox import DockerSandbox
        from agency.infrastructure.sandbox.models import SandboxConfig

        client = docker.from_env()
        client.ping()
        config = SandboxConfig(image="agency-sandbox:latest")
        return DockerSandbox(client=client, config=config)
    except Exception as exc:
        raise RuntimeError(
            f"Unable to connect to Docker daemon: {exc}. "
            "Please ensure Docker is running."
        ) from exc


def _create_default_repository() -> RunRepositoryPort:
    """Create a default in-memory repository for CLI lifecycle tracking."""
    from tests.fakes.fake_run_repository import FakeRunRepository

    return FakeRunRepository()


def _create_default_event_bus() -> EventBusPort:
    """Create a default in-memory event bus for CLI event publication."""
    from tests.fakes.fake_event_bus import FakeEventBus

    return FakeEventBus()


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the agency CLI."""
    parser = argparse.ArgumentParser(
        prog="agency",
        description="Agency: AI-powered software agency CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available commands")

    # Command: agency run <brief_json> --no-llm
    run_parser = subparsers.add_parser(
        "run",
        help="Run the website generation pipeline against a client brief",
    )
    run_parser.add_argument(
        "brief",
        type=Path,
        help="Path to the client brief JSON file",
    )
    run_parser.add_argument(
        "--no-llm",
        dest="no_llm",
        action="store_true",
        default=False,
        help="Execute deterministic pipeline without LLM (required in Phase 5)",
    )
    run_parser.add_argument(
        "--template-dir",
        type=Path,
        default=None,
        help="Optional path to custom template directory",
    )
    run_parser.add_argument(
        "--runs-dir",
        type=Path,
        default=None,
        help="Optional path to output runs directory (defaults to ./runs)",
    )
    run_parser.add_argument(
        "--project-id",
        type=str,
        default=None,
        help="Optional project ID override",
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
    repository: RunRepositoryPort | None = None,
    event_bus: EventBusPort | None = None,
    sandbox: SandboxPort | None = None,
) -> int:
    """CLI entry point for the agency command."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 0

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand == "run":
        # 1. Require explicit --no-llm flag in Phase 5
        if not args.no_llm:
            sys.stderr.write(
                "Error: Phase 5 only supports deterministic pipeline execution. "
                "The '--no-llm' flag is required.\n"
                "Usage: agency run brief.json --no-llm\n"
            )
            return 1

        # 2. Check brief file existence
        brief_path: Path = args.brief
        if not brief_path.is_file():
            sys.stderr.write(f"Error: Brief file not found at '{brief_path}'.\n")
            return 1

        # 3. Read and parse JSON
        try:
            raw_text = brief_path.read_text(encoding="utf-8")
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            sys.stderr.write(
                f"Error: Brief file '{brief_path}' contains malformed JSON:\n"
                f"  Line {exc.lineno}, Column {exc.colno}: {exc.msg}\n"
            )
            return 1
        except Exception as exc:
            sys.stderr.write(f"Error reading brief file: {exc}\n")
            return 1

        # 4. Validate Brief against domain model
        try:
            brief = Brief.model_validate(data)
        except ValidationError as exc:
            sys.stderr.write(f"Error: Brief file '{brief_path}' failed validation:\n")
            for err in exc.errors():
                loc = ".".join(str(p) for p in err.get("loc", []))
                msg = err.get("msg", "")
                sys.stderr.write(f"  - {loc}: {msg}\n")
            return 1

        # 5. Initialize dependencies
        try:
            active_repo = repository or _create_default_repository()
            active_bus = event_bus or _create_default_event_bus()
            active_sandbox = sandbox or _create_default_sandbox()
        except Exception as exc:
            sys.stderr.write(f"Error initializing pipeline infrastructure: {exc}\n")
            return 1

        # 6. Progress reporting callback
        def on_stage(stage: str, msg: str) -> None:
            sys.stdout.write(f"[agency] [{stage}] {msg}\n")
            sys.stdout.flush()

        use_case = RunDeterministicPipeline(
            repository=active_repo,
            event_bus=active_bus,
            sandbox=active_sandbox,
            template_dir=args.template_dir,
            runs_dir=args.runs_dir,
            on_stage=on_stage,
        )

        command = RunDeterministicPipelineCommand(
            brief=brief,
            project_id=args.project_id,
            template_dir=args.template_dir,
            runs_dir=args.runs_dir,
        )

        try:
            result = use_case.execute(command)
        except PipelineExecutionError as exc:
            sys.stderr.write(
                f"\n[agency] FAILED at stage '{exc.stage}': {exc.message}\n"
            )
            return 1
        except Exception as exc:
            sys.stderr.write(f"\n[agency] FAILED: {exc}\n")
            return 1

        # 7. Print success results
        sys.stdout.write("\n=======================================================\n")
        sys.stdout.write("  AGENCY PIPELINE COMPLETED SUCCESSFULLY\n")
        sys.stdout.write("=======================================================\n")
        sys.stdout.write(f"Run ID:       {result.run_id}\n")
        sys.stdout.write(f"Project ID:   {result.project_id}\n")
        sys.stdout.write(f"Status:       {result.status.value}\n")
        sys.stdout.write(f"Variant:      {result.variant}\n")
        sys.stdout.write(f"Screenshots:  {len(result.screenshots)}/8 captured\n")
        sys.stdout.write(f"Artifact Dir: {result.artifact_dir}\n")
        sys.stdout.write(f"Manifest:     {result.manifest_path}\n")
        sys.stdout.write(f"Summary:      {result.summary_path}\n")
        sys.stdout.write("=======================================================\n")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
