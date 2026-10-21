"""In-memory fake implementation of TracingPort for isolated testing."""

import uuid
from dataclasses import dataclass, field
from typing import Any

from agency.application.ports.tracing import (
    SpanContext,
    TraceContext,
    TracingPort,
)


@dataclass
class RecordedGeneration:
    trace_id: str
    span_id: str | None
    name: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecordedScore:
    trace_id: str
    name: str
    value: float
    comment: str | None


@dataclass
class EndedSpan:
    span: SpanContext
    status: str
    error: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


class FakeTracing(TracingPort):
    """In-memory fake recording all traces, spans, and generations for assertions."""

    def __init__(self) -> None:
        self.traces: list[TraceContext] = []
        self.trace_metadata: dict[str, dict[str, Any]] = {}
        self.spans: list[SpanContext] = []
        self.ended_spans: list[EndedSpan] = []
        self.generations: list[RecordedGeneration] = []
        self.scores: list[RecordedScore] = []
        self.flushed: bool = False
        self.shutdown_called: bool = False

    def start_trace(
        self,
        run_id: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> TraceContext:
        ctx = TraceContext(
            trace_id=f"fake-trace-{run_id}",
            run_id=run_id,
            name=name,
        )
        self.traces.append(ctx)
        self.trace_metadata[ctx.trace_id] = dict(metadata or {})
        return ctx

    def start_span(
        self,
        trace_id: str,
        name: str,
        parent_span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SpanContext:
        ctx = SpanContext(
            span_id=f"fake-span-{uuid.uuid4().hex[:8]}",
            trace_id=trace_id,
            name=name,
            parent_span_id=parent_span_id,
        )
        self.spans.append(ctx)
        return ctx

    def end_span(
        self,
        span: SpanContext,
        status: str = "success",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.ended_spans.append(
            EndedSpan(
                span=span,
                status=status,
                error=error,
                metadata=dict(metadata or {}),
            )
        )

    def record_generation(
        self,
        trace_id: str,
        span_id: str | None,
        name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.generations.append(
            RecordedGeneration(
                trace_id=trace_id,
                span_id=span_id,
                name=name,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                metadata=dict(metadata or {}),
            )
        )

    def record_score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> None:
        self.scores.append(
            RecordedScore(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment,
            )
        )

    def flush(self) -> None:
        self.flushed = True

    def shutdown(self) -> None:
        self.shutdown_called = True

    def has_trace(self, run_id: str) -> bool:
        """Check if a trace exists for run_id."""
        return any(t.run_id == run_id for t in self.traces)

    def clear(self) -> None:
        """Reset all recorded traces, spans, generations, and scores."""
        self.traces.clear()
        self.trace_metadata.clear()
        self.spans.clear()
        self.ended_spans.clear()
        self.generations.clear()
        self.scores.clear()
        self.flushed = False
        self.shutdown_called = False
