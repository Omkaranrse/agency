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
    from agency.infrastructure.persistence.in_memory_run_repository import (
        InMemoryRunRepository,
    )

    return InMemoryRunRepository()


def _create_default_event_bus() -> EventBusPort:
    """Create a default in-memory event bus for CLI event publication."""
    from agency.infrastructure.adapters.in_memory.event_bus import (
        InMemoryEventBus,
    )

    return InMemoryEventBus()


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

    # Command: agency export-openapi
    openapi_parser = subparsers.add_parser(
        "export-openapi",
        help="Export the OpenAPI JSON schema to a file",
    )
    openapi_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("docs/openapi.json"),
        help="Output path for OpenAPI JSON (defaults to docs/openapi.json)",
    )

    # Command: agency eval
    eval_parser = subparsers.add_parser(
        "eval",
        help="Evaluation framework commands for website generation quality",
    )
    eval_subparsers = eval_parser.add_subparsers(
        dest="eval_subcommand", help="Evaluation subcommands"
    )

    # agency eval run
    eval_run_parser = eval_subparsers.add_parser(
        "run",
        help="Run evaluations against test briefs",
    )
    eval_run_parser.add_argument(
        "--mode",
        choices=["fake", "real"],
        default="fake",
        help="Evaluation execution mode ('fake' or 'real')",
    )
    eval_run_parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to evaluation dataset directory containing briefs",
    )
    eval_run_parser.add_argument(
        "--brief",
        type=str,
        default=None,
        help="Target individual brief name (e.g. 'developer')",
    )
    eval_run_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs/evals"),
        help="Directory to save evaluation reports",
    )
    eval_run_parser.add_argument(
        "--max-budget",
        type=float,
        default=None,
        help="Maximum budget in USD for real LLM evaluations",
    )

    # agency eval report
    eval_report_parser = eval_subparsers.add_parser(
        "report",
        help="Display or locate reports for an evaluation run",
    )
    eval_report_parser.add_argument(
        "--run-id",
        required=True,
        help="Evaluation run ID to locate report for",
    )
    eval_report_parser.add_argument(
        "--runs-dir",
        type=Path,
        default=Path("runs/evals"),
        help="Directory where evaluation reports are stored",
    )

    # agency cleanup
    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="Purge orphaned sandbox containers and expired temporary workspaces",
    )
    cleanup_parser.add_argument(
        "--retention-hours",
        type=float,
        default=24.0,
        help="Prune temporary resources older than this threshold in hours",
    )
    cleanup_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report resources eligible for removal without destroying them",
    )

    # agency serve
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the Agency FastAPI REST API server",
    )
    serve_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Bind socket host (defaults to 0.0.0.0)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind socket port (defaults to 8000)",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable auto-reload on source file changes",
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

    if args.subcommand == "serve":
        import uvicorn

        sys.stdout.write(
            f"Starting Agency API server on {args.host}:{args.port} "
            f"(reload={args.reload})...\n"
        )
        uvicorn.run(
            "agency.interfaces.api.app:create_app",
            factory=True,
            host=args.host,
            port=args.port,
            reload=args.reload,
        )
        return 0

    if args.subcommand == "export-openapi":
        from agency.interfaces.api.openapi import export_openapi_json

        out_file = export_openapi_json(args.output)
        sys.stdout.write(f"OpenAPI schema successfully exported to: {out_file}\n")
        return 0

    if args.subcommand == "eval":
        if not getattr(args, "eval_subcommand", None):
            parser.parse_args(["eval", "--help"])
            return 0

        if args.eval_subcommand == "run":
            from evals.runner import EvaluationRunner

            runner = EvaluationRunner(
                dataset_dir=args.dataset,
                output_base_dir=args.output_dir,
                mode=args.mode,
            )
            summary = runner.run_suite(
                target_brief_id=args.brief,
                max_budget_usd=args.max_budget,
            )
            out_dir = args.output_dir / summary.eval_run_id
            sys.stdout.write(
                "\n=======================================================\n"
            )
            sys.stdout.write(f"  AGENCY EVALUATION COMPLETED: {summary.eval_run_id}\n")
            sys.stdout.write(
                "=======================================================\n"
            )
            sys.stdout.write(f"Mode:             {summary.mode}\n")
            sys.stdout.write(f"Briefs Evaluated: {summary.briefs_attempted}\n")
            build_stat = (
                f"{summary.successful_builds}/{summary.briefs_attempted} "
                f"({summary.build_success_rate * 100:.1f}%)"
            )
            sys.stdout.write(f"Build Success:    {build_stat}\n")
            sys.stdout.write(f"QA Pass Rate:     {summary.qa_pass_rate * 100:.1f}%\n")
            sys.stdout.write(f"Avg Duration:     {summary.avg_duration_seconds:.2f}s\n")
            sys.stdout.write(f"Avg Copy Quality: {summary.avg_copy_quality:.1f}/10.0\n")
            sys.stdout.write(
                f"Actual Cost:      ${summary.total_actual_cost_usd:.4f}\n"
            )
            sys.stdout.write(
                f"Estimated Cost:   ${summary.total_estimated_cost_usd:.4f}\n"
            )
            sys.stdout.write(f"Reports Written:  {out_dir}\n")
            sys.stdout.write(f"  - Markdown:     {out_dir / 'report.md'}\n")
            sys.stdout.write(f"  - CSV:          {out_dir / 'results.csv'}\n")
            sys.stdout.write(
                "=======================================================\n"
            )
            return 0 if summary.failed_evaluations_count == 0 else 1

        if args.eval_subcommand == "report":
            report_dir = args.runs_dir / args.run_id
            md_file = report_dir / "report.md"
            if not md_file.exists():
                sys.stderr.write(
                    f"Error: Report for run ID '{args.run_id}' not found "
                    f"at '{report_dir}'.\n"
                )
                return 1
            sys.stdout.write(md_file.read_text(encoding="utf-8"))
            return 0

    if args.subcommand == "cleanup":
        from agency.application.services.cleanup_service import CleanupService

        repo = repository or _create_default_repository()
        service = CleanupService(repository=repo)
        cleanup_summary = service.run_cleanup(
            retention_hours=args.retention_hours,
            dry_run=args.dry_run,
        )

        sys.stdout.write("\n=======================================================\n")
        mode_str = "DRY-RUN (Simulated)" if cleanup_summary.dry_run else "ACTIVE"
        sys.stdout.write(f"  AGENCY MAINTENANCE CLEANUP: {mode_str}\n")
        sys.stdout.write("=======================================================\n")
        sys.stdout.write(
            f"Active Runs Protected:   {cleanup_summary.active_runs_protected}\n"
        )
        sys.stdout.write(
            f"Containers Inspected:    {cleanup_summary.containers_inspected}\n"
        )
        sys.stdout.write(
            f"Containers Removed:      {len(cleanup_summary.containers_removed)}\n"
        )
        sys.stdout.write(
            f"Workspaces Inspected:    {cleanup_summary.workspaces_inspected}\n"
        )
        sys.stdout.write(
            f"Workspaces Removed:      {len(cleanup_summary.workspaces_removed)}\n"
        )
        sys.stdout.write(
            f"Bytes Reclaimed:         {cleanup_summary.bytes_reclaimed:,} bytes\n"
        )
        if cleanup_summary.errors:
            sys.stdout.write(
                f"Errors Encountered:      {len(cleanup_summary.errors)}\n"
            )
            for err in cleanup_summary.errors:
                sys.stdout.write(f"  - {err}\n")
        sys.stdout.write("=======================================================\n")
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
            for val_err in exc.errors():
                loc = ".".join(str(p) for p in val_err.get("loc", []))
                msg = val_err.get("msg", "")
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
