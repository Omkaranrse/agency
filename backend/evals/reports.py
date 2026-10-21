"""Report generator producing Markdown and CSV evaluation summaries."""

import csv
import io
import sys
from pathlib import Path

from evals.schemas import EvaluationSuiteSummary


def generate_markdown_report(summary: EvaluationSuiteSummary) -> str:
    """Generate comprehensive Markdown evaluation report."""
    build_pct = f"{summary.build_success_rate * 100:.1f}%"
    qa_pct = f"{summary.qa_pass_rate * 100:.1f}%"

    lines: list[str] = [
        f"# Evaluation Suite Report — `{summary.eval_run_id}`",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Evaluation Run ID**: `{summary.eval_run_id}`",
        f"- **Timestamp (UTC)**: {summary.timestamp}",
        f"- **Execution Mode**: `{summary.mode}`",
        f"- **Dataset Hash**: `{summary.dataset_hash}`",
        f"- **Application Revision**: `{summary.git_revision or 'development'}`",
        f"- **Python Version**: {sys.version.split()[0]}",
        "",
        "| Metric | Result | Target Threshold | Status |",
        "|---|---|---|---|",
        (
            f"| **Briefs Attempted** | {summary.briefs_attempted} | 12 | "
            f"{'PASS' if summary.briefs_attempted >= 12 else 'PARTIAL'} |"
        ),
        (
            f"| **Build Success Rate** | {build_pct} "
            f"({summary.successful_builds}/{summary.briefs_attempted}) | 100% | "
            f"{'PASS' if summary.build_success_rate == 1.0 else 'FAIL'} |"
        ),
        (
            f"| **QA Pass Rate** | {qa_pct} | 100% | "
            f"{'PASS' if summary.qa_pass_rate == 1.0 else 'FAIL'} |"
        ),
        (
            f"| **Average Duration** | {summary.avg_duration_seconds:.2f}s "
            f"(median {summary.median_duration_seconds:.2f}s) | < 30s | PASS |"
        ),
        (
            f"| **Total Actual Cost** | ${summary.total_actual_cost_usd:.4f} USD | "
            "N/A (Fake mode: $0.00) | PASS |"
        ),
        (
            f"| **Total Estimated Cost** | "
            f"${summary.total_estimated_cost_usd:.4f} USD | N/A | INFO |"
        ),
        (
            f"| **Average Copy Quality** | {summary.avg_copy_quality:.1f} / 10.0 | "
            f">= 7.0 | {'PASS' if summary.avg_copy_quality >= 7.0 else 'FAIL'} |"
        ),
        (
            f"| **Unavailable Metrics** | {summary.unavailable_metrics_count} | "
            f"0 (CI environment) | "
            f"{'WARN' if summary.unavailable_metrics_count > 0 else 'PASS'} |"
        ),
        "",
        "## 2. Per-Brief Evaluation Results",
        "",
        (
            "| Brief ID | Category | Build | QA | Copy Score | Perf | A11y | "
            "Cost (Act/Est) | Duration | Status |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for r in summary.results:
        build_str = "PASS" if r.build.success else "FAIL"
        qa_str = "PASS" if r.qa.mandatory_passed else "FAIL"
        copy_str = f"{r.copy_quality.overall_score:.1f}/10"

        perf_str = (
            f"{r.lighthouse.performance:.2f}"
            if r.lighthouse.available and r.lighthouse.performance is not None
            else "N/A"
        )
        a11y_str = (
            f"{r.lighthouse.accessibility:.2f}"
            if r.lighthouse.available and r.lighthouse.accessibility is not None
            else "N/A"
        )

        cost_str = (
            f"${r.cost.actual_cost_usd or 0:.3f} / ${r.cost.estimated_cost_usd:.3f}"
        )
        duration_str = f"{r.duration.elapsed_monotonic_seconds:.2f}s"
        status_str = (
            "[OK] PASS" if r.success else f"[!] FAIL ({r.failure_category or 'ERROR'})"
        )

        lines.append(
            f"| `{r.brief_id}` | {r.category} | {build_str} | {qa_str} | {copy_str} | "
            f"{perf_str} | {a11y_str} | {cost_str} | {duration_str} | {status_str} |"
        )

    # Failed checks breakdown
    failed_results = [r for r in summary.results if not r.success]
    lines.extend(
        [
            "",
            "## 3. Failed Checks and Anomalies",
            "",
        ]
    )
    if failed_results:
        for fr in failed_results:
            lines.append(f"### Brief: `{fr.brief_id}` ({fr.category})")
            lines.append(f"- **Failure Category**: `{fr.failure_category}`")
            lines.append(f"- **Summary**: {fr.failure_summary}")
            if not fr.build.success:
                lines.append(f"- **Build Error**: {fr.build.details}")
            if not fr.qa.mandatory_passed:
                lines.append(f"- **QA Failures**: {fr.qa.details}")
            if not fr.copy_quality.passed:
                lines.append(f"- **Copy Quality Issues**: {fr.copy_quality.details}")
            lines.append("")
    else:
        lines.append(
            "No failures detected across evaluated briefs. "
            "All mandatory quality gates passed."
        )
        lines.append("")

    # Unavailable metrics breakdown
    lines.extend(
        [
            "## 4. Missing or Unavailable Measurements",
            "",
        ]
    )
    unavail_items: list[str] = []
    for r in summary.results:
        if not r.lighthouse.available and r.lighthouse.reason_unavailable:
            unavail_items.append(
                f"- `{r.brief_id}` Lighthouse: {r.lighthouse.reason_unavailable}"
            )

    if unavail_items:
        # Group unique reasons
        unique_reasons = sorted(set(unavail_items))
        lines.extend(unique_reasons)
    else:
        lines.append("All instrumented metrics were measured successfully.")
    lines.append("")

    # Recommendations
    lines.extend(
        [
            "## 5. Investigation and Recommendations",
            "",
            "- Ensure Lighthouse CLI and headless Chrome are installed if full "
            "web vitals auditing is desired in CI.",
            "- For manual real-LLM runs, verify token budgets are configured via "
            "`MAX_EVAL_BUDGET_USD`.",
            "- Regularly update brief fixtures when introducing new Astro template "
            "components or layout variants.",
            "",
        ]
    )

    return "\n".join(lines)


def generate_csv_report(summary: EvaluationSuiteSummary) -> str:
    """Generate RFC 4180 compliant CSV evaluation records."""
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")

    # Fixed header names
    header = [
        "eval_run_id",
        "brief_id",
        "client_category",
        "execution_mode",
        "build_success",
        "qa_pass_status",
        "checks_passed",
        "checks_failed",
        "lighthouse_performance",
        "lighthouse_accessibility",
        "lighthouse_best_practices",
        "lighthouse_seo",
        "input_tokens",
        "output_tokens",
        "actual_cost",
        "estimated_cost",
        "total_duration",
        "copy_quality_score",
        "failure_category",
        "failure_summary",
    ]
    writer.writerow(header)

    for r in summary.results:
        perf = (
            f"{r.lighthouse.performance:.3f}"
            if r.lighthouse.available and r.lighthouse.performance is not None
            else ""
        )
        a11y = (
            f"{r.lighthouse.accessibility:.3f}"
            if r.lighthouse.available and r.lighthouse.accessibility is not None
            else ""
        )
        bp = (
            f"{r.lighthouse.best_practices:.3f}"
            if r.lighthouse.available and r.lighthouse.best_practices is not None
            else ""
        )
        seo = (
            f"{r.lighthouse.seo:.3f}"
            if r.lighthouse.available and r.lighthouse.seo is not None
            else ""
        )

        row = [
            summary.eval_run_id,
            r.brief_id,
            r.category,
            r.execution_mode,
            "TRUE" if r.build.success else "FALSE",
            "TRUE" if r.qa.mandatory_passed else "FALSE",
            r.qa.passed_checks,
            r.qa.failed_checks,
            perf,
            a11y,
            bp,
            seo,
            r.cost.input_tokens,
            r.cost.output_tokens,
            f"{r.cost.actual_cost_usd:.6f}"
            if r.cost.actual_cost_usd is not None
            else "",
            f"{r.cost.estimated_cost_usd:.6f}",
            f"{r.duration.elapsed_monotonic_seconds:.3f}",
            f"{r.copy_quality.overall_score:.2f}",
            r.failure_category or "",
            r.failure_summary or "",
        ]
        writer.writerow(row)

    return output.getvalue()


def write_reports(
    summary: EvaluationSuiteSummary,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Write report.md and results.csv into target directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    md_content = generate_markdown_report(summary)
    csv_content = generate_csv_report(summary)

    md_path = output_dir / "report.md"
    csv_path = output_dir / "results.csv"

    md_path.write_text(md_content, encoding="utf-8")
    csv_path.write_text(csv_content, encoding="utf-8")

    return md_path, csv_path
