"""Aggregate statistics and comparison metrics for evaluation suites."""

import hashlib
import statistics
from pathlib import Path

from evals.schemas import BriefEvaluationResult, EvaluationSuiteSummary


def compute_dataset_hash(dataset_dir: Path) -> str:
    """Compute deterministic SHA-256 hash across all JSON brief files in a directory."""
    if not dataset_dir.is_dir():
        return "empty"
    hasher = hashlib.sha256()
    for file in sorted(dataset_dir.glob("*.json")):
        hasher.update(file.name.encode("utf-8"))
        hasher.update(file.read_bytes())
    return hasher.hexdigest()[:16]


def aggregate_results(
    eval_run_id: str,
    timestamp: str,
    mode: str,
    dataset_hash: str,
    results: list[BriefEvaluationResult],
    git_revision: str | None = None,
) -> EvaluationSuiteSummary:
    """Compute aggregate statistics across briefs without divide-by-zero errors."""
    total_attempted = len(results)

    if total_attempted == 0:
        return EvaluationSuiteSummary(
            eval_run_id=eval_run_id,
            timestamp=timestamp,
            mode=mode,
            dataset_hash=dataset_hash,
            git_revision=git_revision,
            briefs_attempted=0,
            successful_builds=0,
            build_success_rate=0.0,
            qa_pass_rate=0.0,
            avg_lighthouse_performance=None,
            median_lighthouse_performance=None,
            avg_lighthouse_accessibility=None,
            avg_lighthouse_best_practices=None,
            avg_lighthouse_seo=None,
            avg_duration_seconds=0.0,
            median_duration_seconds=0.0,
            total_actual_cost_usd=0.0,
            total_estimated_cost_usd=0.0,
            avg_copy_quality=0.0,
            unavailable_metrics_count=0,
            failed_evaluations_count=0,
            results=[],
        )

    successful_builds = sum(1 for r in results if r.build.success)
    build_success_rate = round(successful_builds / total_attempted, 4)

    qa_passed_count = sum(1 for r in results if r.qa.mandatory_passed)
    qa_pass_rate = round(qa_passed_count / total_attempted, 4)

    # Durations
    durations = [r.duration.elapsed_monotonic_seconds for r in results]
    avg_duration = round(statistics.mean(durations), 3) if durations else 0.0
    med_duration = round(statistics.median(durations), 3) if durations else 0.0

    # Costs
    total_actual_cost = round(sum(r.cost.actual_cost_usd or 0.0 for r in results), 6)
    total_estimated_cost = round(sum(r.cost.estimated_cost_usd for r in results), 6)

    # Copy quality
    avg_copy_quality = round(
        sum(r.copy_quality.overall_score for r in results) / total_attempted, 2
    )

    # Lighthouse valid measurements
    def _metric_stats(attr: str) -> tuple[float | None, float | None]:
        vals = [
            getattr(r.lighthouse, attr)
            for r in results
            if r.lighthouse.available and getattr(r.lighthouse, attr) is not None
        ]
        if not vals:
            return None, None
        return round(statistics.mean(vals), 3), round(statistics.median(vals), 3)

    perf_avg, perf_med = _metric_stats("performance")
    a11y_avg, _ = _metric_stats("accessibility")
    bp_avg, _ = _metric_stats("best_practices")
    seo_avg, _ = _metric_stats("seo")

    unavailable_count = sum(1 for r in results if not r.lighthouse.available)
    failed_evals = sum(1 for r in results if not r.success)

    return EvaluationSuiteSummary(
        eval_run_id=eval_run_id,
        timestamp=timestamp,
        mode=mode,
        dataset_hash=dataset_hash,
        git_revision=git_revision,
        briefs_attempted=total_attempted,
        successful_builds=successful_builds,
        build_success_rate=build_success_rate,
        qa_pass_rate=qa_pass_rate,
        avg_lighthouse_performance=perf_avg,
        median_lighthouse_performance=perf_med,
        avg_lighthouse_accessibility=a11y_avg,
        avg_lighthouse_best_practices=bp_avg,
        avg_lighthouse_seo=seo_avg,
        avg_duration_seconds=avg_duration,
        median_duration_seconds=med_duration,
        total_actual_cost_usd=total_actual_cost,
        total_estimated_cost_usd=total_estimated_cost,
        avg_copy_quality=avg_copy_quality,
        unavailable_metrics_count=unavailable_count,
        failed_evaluations_count=failed_evals,
        results=results,
    )
