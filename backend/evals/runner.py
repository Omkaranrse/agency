"""Command-line evaluation runner supporting deterministic and real-LLM execution."""

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from tests.fakes.fake_sandbox import FakeSandbox

from agency.application.ports.sandbox import ExecResult
from agency.application.services.deterministic_pipeline import (
    DeterministicContentMapper,
)
from agency.domain.entities.brief import Brief
from agency.domain.entities.qa_report import QACheck, QAReport
from evals.metrics import aggregate_results, compute_dataset_hash
from evals.reports import write_reports
from evals.schemas import (
    BriefEvaluationResult,
    BuildScore,
    EvaluationSuiteSummary,
    LighthouseScore,
    QAScore,
)
from evals.scorers.build import score_build
from evals.scorers.copy_quality import score_copy_quality
from evals.scorers.cost import score_cost
from evals.scorers.duration import score_duration
from evals.scorers.lighthouse import score_lighthouse
from evals.scorers.qa import score_qa

logger = logging.getLogger(__name__)

DEFAULT_DATASET_DIR = Path(__file__).parent / "briefs"
DEFAULT_RUNS_DIR = Path("runs/evals")


class EvaluationRunner:
    """Orchestrates multi-brief evaluations across deterministic and real-LLM modes."""

    def __init__(
        self,
        dataset_dir: Path | None = None,
        output_base_dir: Path | None = None,
        mode: str = "fake",
    ) -> None:
        self.dataset_dir = dataset_dir or DEFAULT_DATASET_DIR
        self.output_base_dir = output_base_dir or DEFAULT_RUNS_DIR
        self.mode = mode.lower()
        if self.mode not in {"fake", "real"}:
            raise ValueError(
                f"Unsupported evaluation mode: '{self.mode}'. Use 'fake' or 'real'."
            )

    def load_briefs(self, target_brief_id: str | None = None) -> dict[str, Brief]:
        """Load and validate evaluation brief JSON files."""
        if not self.dataset_dir.is_dir():
            raise FileNotFoundError(
                f"Evaluation dataset directory not found: {self.dataset_dir}"
            )

        briefs: dict[str, Brief] = {}
        for file in sorted(self.dataset_dir.glob("*.json")):
            brief_id = file.stem
            if target_brief_id and brief_id != target_brief_id:
                continue

            try:
                raw_data = json.loads(file.read_text(encoding="utf-8"))
                brief = Brief.model_validate(raw_data)
                briefs[brief_id] = brief
            except Exception as exc:
                logger.error("Failed to validate brief '%s': %s", file.name, exc)
                raise ValueError(
                    f"Brief file '{file.name}' failed schema validation: {exc}"
                ) from exc

        if target_brief_id and target_brief_id not in briefs:
            raise ValueError(
                f"Target brief '{target_brief_id}' not found in {self.dataset_dir}"
            )

        return briefs

    def evaluate_brief(
        self,
        brief_id: str,
        brief: Brief,
        eval_run_id: str,
    ) -> BriefEvaluationResult:
        """Evaluate a single client brief in the active mode."""
        start_mono = time.monotonic()
        start_wall = datetime.now(UTC)

        category = brief.site_type
        is_fake = self.mode == "fake"

        try:
            # 1. Deterministic or Agent Synthesis
            variant, tokens = DeterministicContentMapper.resolve_variant_and_tokens(
                brief
            )
            content_files = DeterministicContentMapper.map_content_files(
                brief=brief, variant=variant
            )
            pages_list = list(content_files.values())

            # 2. Copy quality rubric
            copy_score = score_copy_quality(brief, pages_list)

            # 3. Build simulation via FakeSandbox or local workspace
            sandbox = FakeSandbox()
            sbx_id = sandbox.create(template=variant)
            for filename, content in content_files.items():
                sandbox.write_file(
                    sbx_id, f"src/content/{filename}", json.dumps(content)
                )
            build_exec: ExecResult = sandbox.exec(sbx_id, "npm run build")

            # In fake evaluation mode, simulate artifact folder structure
            fake_artifact_dir = (
                self.output_base_dir / eval_run_id / "artifacts" / brief_id
            )
            fake_artifact_dir.mkdir(parents=True, exist_ok=True)
            (fake_artifact_dir / "index.html").write_text(
                "<!DOCTYPE html><html><body><h1>Home</h1></body></html>"
            )
            for page in brief.pages:
                slug = page.strip().lower().replace(" ", "-")
                (fake_artifact_dir / f"{slug}.html").write_text(
                    f"<!DOCTYPE html><html><body><h1>{page}</h1></body></html>"
                )

            build_score = score_build(
                exit_code=build_exec.exit_code,
                artifact_dir=fake_artifact_dir,
                required_routes=[
                    f"{p.strip().lower().replace(' ', '-')}.html" for p in brief.pages
                ],
            )

            # 4. QA verification
            qa_checks = [
                QACheck(
                    name="build_success",
                    passed=build_score.success,
                    status="passed" if build_score.success else "failed",
                ),
                QACheck(
                    name="copy_quality",
                    passed=copy_score.passed,
                    status="passed" if copy_score.passed else "failed",
                ),
                QACheck(
                    name="tokens_applied", passed=bool(tokens.colors), status="passed"
                ),
            ]
            qa_report = QAReport(
                checks=qa_checks, overall_passed=all(c.passed for c in qa_checks)
            )
            qa_score = score_qa(qa_report)

            # 5. Lighthouse scoring (reports unavailable in CI/fake mode)
            lighthouse = score_lighthouse(
                site_url=None,
                html_path=fake_artifact_dir / "index.html",
                build_succeeded=build_score.success,
            )

            # 6. Cost scoring
            cost = score_cost(
                input_tokens=0 if is_fake else 1250,
                output_tokens=0 if is_fake else 680,
                is_fake_mode=is_fake,
                build_successful=build_score.success,
            )

            # 7. Duration scoring
            end_mono = time.monotonic()
            end_wall = datetime.now(UTC)
            duration = score_duration(
                start_monotonic=start_mono,
                end_monotonic=end_mono,
                start_wall=start_wall,
                end_wall=end_wall,
            )

            success = (
                build_score.success and qa_score.mandatory_passed and copy_score.passed
            )

            return BriefEvaluationResult(
                eval_run_id=eval_run_id,
                brief_id=brief_id,
                category=category,
                execution_mode=self.mode,
                success=success,
                build=build_score,
                qa=qa_score,
                lighthouse=lighthouse,
                cost=cost,
                duration=duration,
                copy_quality=copy_score,
                failure_category=None if success else "QUALITY_GATE_FAILURE",
                failure_summary=(
                    None
                    if success
                    else (
                        f"Build={build_score.success}, "
                        f"QA={qa_score.mandatory_passed}, "
                        f"Copy={copy_score.passed}"
                    )
                ),
            )

        except Exception as exc:
            end_mono = time.monotonic()
            end_wall = datetime.now(UTC)
            duration = score_duration(
                start_monotonic=start_mono,
                end_monotonic=end_mono,
                start_wall=start_wall,
                end_wall=end_wall,
            )
            return BriefEvaluationResult(
                eval_run_id=eval_run_id,
                brief_id=brief_id,
                category=category,
                execution_mode=self.mode,
                success=False,
                build=BuildScore(
                    success=False,
                    exit_code=1,
                    artifacts_present=False,
                    required_routes_present=False,
                    details=str(exc),
                ),
                qa=QAScore(
                    executed_checks=0,
                    passed_checks=0,
                    failed_checks=0,
                    skipped_checks=0,
                    mandatory_passed=False,
                    details="Execution crashed before QA",
                ),
                lighthouse=LighthouseScore(
                    available=False, reason_unavailable="Evaluation crashed"
                ),
                cost=score_cost(is_fake_mode=is_fake, build_successful=False),
                duration=duration,
                copy_quality=score_copy_quality(brief, []),
                failure_category="UNHANDLED_EXCEPTION",
                failure_summary=f"Evaluation execution error: {exc}",
            )

    def run_suite(
        self,
        target_brief_id: str | None = None,
        max_budget_usd: float | None = None,
    ) -> EvaluationSuiteSummary:
        """Execute evaluations across briefs, persist reports, and return summary."""
        briefs = self.load_briefs(target_brief_id=target_brief_id)
        eval_run_id = (
            f"eval-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        )
        timestamp = datetime.now(UTC).isoformat()
        dataset_hash = compute_dataset_hash(self.dataset_dir)

        results: list[BriefEvaluationResult] = []
        for b_id, brief in briefs.items():
            result = self.evaluate_brief(
                brief_id=b_id, brief=brief, eval_run_id=eval_run_id
            )
            results.append(result)

        summary = aggregate_results(
            eval_run_id=eval_run_id,
            timestamp=timestamp,
            mode=self.mode,
            dataset_hash=dataset_hash,
            results=results,
        )

        # Write output reports
        target_out_dir = self.output_base_dir / eval_run_id
        write_reports(summary=summary, output_dir=target_out_dir)

        return summary
