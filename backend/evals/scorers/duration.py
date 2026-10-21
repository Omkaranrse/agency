"""Duration scorer measuring elapsed time using monotonic clocks."""

from datetime import datetime

from evals.schemas import DurationScore


def score_duration(
    start_monotonic: float,
    end_monotonic: float,
    start_wall: datetime,
    end_wall: datetime,
    model_call_seconds: float = 0.0,
    build_seconds: float = 0.0,
    qa_seconds: float = 0.0,
) -> DurationScore:
    """Compute duration scores using monotonic clocks for elapsed duration."""
    elapsed_monotonic = max(0.0, end_monotonic - start_monotonic)
    wall_clock_seconds = max(0.0, (end_wall - start_wall).total_seconds())

    return DurationScore(
        total_wall_clock_seconds=round(wall_clock_seconds, 3),
        elapsed_monotonic_seconds=round(elapsed_monotonic, 3),
        model_call_seconds=round(model_call_seconds, 3),
        build_seconds=round(build_seconds, 3),
        qa_seconds=round(qa_seconds, 3),
    )
