"""Unit tests for the evaluation runner, report generation, and CLI subcommands."""

import csv
from pathlib import Path

import pytest
from evals.metrics import aggregate_results, compute_dataset_hash
from evals.runner import EvaluationRunner


def test_runner_initialization_validates_mode() -> None:
    """Runner accepts 'fake' and 'real' modes and rejects unsupported modes."""
    runner_fake = EvaluationRunner(mode="fake")
    assert runner_fake.mode == "fake"

    runner_real = EvaluationRunner(mode="real")
    assert runner_real.mode == "real"

    with pytest.raises(ValueError, match="Unsupported evaluation mode"):
        EvaluationRunner(mode="invalid_mode")


def test_runner_loads_briefs_and_filters() -> None:
    """Runner loads all 12 briefs or filters by target brief ID."""
    runner = EvaluationRunner()
    all_briefs = runner.load_briefs()
    assert len(all_briefs) == 12
    assert "developer" in all_briefs

    dev_only = runner.load_briefs(target_brief_id="developer")
    assert len(dev_only) == 1
    assert "developer" in dev_only

    with pytest.raises(ValueError, match="Target brief 'nonexistent' not found"):
        runner.load_briefs(target_brief_id="nonexistent")


def test_runner_executes_fake_suite_and_persists_reports(tmp_path: Path) -> None:
    """Runner executes single-brief suite in fake mode and generates reports."""
    runner = EvaluationRunner(output_base_dir=tmp_path, mode="fake")
    summary = runner.run_suite(target_brief_id="developer")

    assert summary.briefs_attempted == 1
    assert summary.successful_builds == 1
    assert summary.build_success_rate == 1.0
    assert summary.qa_pass_rate == 1.0
    assert summary.total_actual_cost_usd == 0.0
    assert summary.failed_evaluations_count == 0

    run_dir = tmp_path / summary.eval_run_id
    assert (run_dir / "report.md").is_file()
    assert (run_dir / "results.csv").is_file()

    # Verify CSV format and headers
    csv_text = (run_dir / "results.csv").read_text(encoding="utf-8")
    reader = csv.reader(csv_text.splitlines())
    rows = list(reader)
    assert len(rows) == 2  # Header + 1 brief record

    header = rows[0]
    assert len(header) == 20
    assert "eval_run_id" in header
    assert "brief_id" in header
    assert "copy_quality_score" in header

    record = rows[1]
    assert record[1] == "developer"
    assert record[3] == "fake"
    assert record[4] == "TRUE"  # build_success
    assert record[5] == "TRUE"  # qa_pass_status


def test_aggregate_results_handles_zero_briefs() -> None:
    """aggregate_results handles zero-result datasets without zero division."""
    summary = aggregate_results(
        eval_run_id="eval-empty",
        timestamp="2026-01-01T00:00:00Z",
        mode="fake",
        dataset_hash="empty",
        results=[],
    )
    assert summary.briefs_attempted == 0
    assert summary.build_success_rate == 0.0
    assert summary.qa_pass_rate == 0.0
    assert summary.avg_duration_seconds == 0.0
    assert summary.avg_copy_quality == 0.0
    assert summary.total_actual_cost_usd == 0.0


def test_dataset_hash_is_deterministic(tmp_path: Path) -> None:
    """Dataset hash computation is deterministic and changes when briefs change."""
    d1 = tmp_path / "d1"
    d1.mkdir()
    (d1 / "a.json").write_text('{"name": "a"}')
    (d1 / "b.json").write_text('{"name": "b"}')

    hash1 = compute_dataset_hash(d1)
    hash2 = compute_dataset_hash(d1)
    assert hash1 == hash2

    # Change content
    (d1 / "b.json").write_text('{"name": "b_modified"}')
    hash3 = compute_dataset_hash(d1)
    assert hash1 != hash3
