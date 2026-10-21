"""Data schemas for the evaluation framework, metric scorers, and reports."""

from pydantic import BaseModel, ConfigDict, Field


class BuildScore(BaseModel):
    """Evaluation result for static website compilation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    success: bool
    exit_code: int
    artifacts_present: bool
    required_routes_present: bool
    details: str = ""


class QAScore(BaseModel):
    """Evaluation result for automated QA checks."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    executed_checks: int
    passed_checks: int
    failed_checks: int
    skipped_checks: int
    mandatory_passed: bool
    details: str = ""


class LighthouseScore(BaseModel):
    """Audit scores from Lighthouse or explicit unavailable status."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    available: bool
    reason_unavailable: str | None = None
    performance: float | None = None
    accessibility: float | None = None
    best_practices: float | None = None
    seo: float | None = None


class CostScore(BaseModel):
    """Token usage and monetary cost accounting."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    actual_cost_usd: float | None = None
    estimated_cost_usd: float = 0.0
    cost_per_successful_build: float = 0.0


class DurationScore(BaseModel):
    """Timing breakdown for pipeline execution in seconds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_wall_clock_seconds: float
    elapsed_monotonic_seconds: float
    model_call_seconds: float = 0.0
    build_seconds: float = 0.0
    qa_seconds: float = 0.0


class CopyQualityRubricScore(BaseModel):
    """Deterministic rubric scoring for synthesized website content."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    brief_alignment: float = Field(ge=0.0, le=10.0)
    section_completeness: float = Field(ge=0.0, le=10.0)
    specificity_and_relevance: float = Field(ge=0.0, le=10.0)
    readability: float = Field(ge=0.0, le=10.0)
    tone_consistency: float = Field(ge=0.0, le=10.0)
    absence_of_unsupported_claims: float = Field(ge=0.0, le=10.0)
    absence_of_placeholders: float = Field(ge=0.0, le=10.0)
    overall_score: float = Field(ge=0.0, le=10.0)
    passed: bool
    detected_placeholders: list[str] = Field(default_factory=list)
    details: str = ""


class BriefEvaluationResult(BaseModel):
    """Complete evaluation outcome for an individual client brief."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    eval_run_id: str
    brief_id: str
    category: str
    execution_mode: str  # 'fake' or 'real'
    success: bool
    build: BuildScore
    qa: QAScore
    lighthouse: LighthouseScore
    cost: CostScore
    duration: DurationScore
    copy_quality: CopyQualityRubricScore
    failure_category: str | None = None
    failure_summary: str | None = None


class EvaluationSuiteSummary(BaseModel):
    """Aggregate statistics and comparison metrics for a completed suite."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    eval_run_id: str
    timestamp: str
    mode: str
    dataset_hash: str
    git_revision: str | None
    briefs_attempted: int
    successful_builds: int
    build_success_rate: float
    qa_pass_rate: float
    avg_lighthouse_performance: float | None
    median_lighthouse_performance: float | None
    avg_lighthouse_accessibility: float | None
    avg_lighthouse_best_practices: float | None
    avg_lighthouse_seo: float | None
    avg_duration_seconds: float
    median_duration_seconds: float
    total_actual_cost_usd: float
    total_estimated_cost_usd: float
    avg_copy_quality: float
    unavailable_metrics_count: int
    failed_evaluations_count: int
    results: list[BriefEvaluationResult]
