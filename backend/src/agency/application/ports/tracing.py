"""Tracing port definition for distributed workflow observability."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class TraceContext:
    """Represents an active root trace correlated with a workflow run."""

    trace_id: str
    run_id: str
    name: str
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class SpanContext:
    """Represents an active child operation within a trace."""

    span_id: str
    trace_id: str
    name: str
    parent_span_id: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TracingPort(ABC):
    """Abstract port for distributed tracing, span tracking, and generation metrics."""

    @abstractmethod
    def start_trace(
        self,
        run_id: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> TraceContext:
        """Initialize and return a root trace correlated with run_id."""

    @abstractmethod
    def start_span(
        self,
        trace_id: str,
        name: str,
        parent_span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SpanContext:
        """Start a child operation span within a trace."""

    @abstractmethod
    def end_span(
        self,
        span: SpanContext,
        status: str = "success",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Complete a span, recording its status, errors, and updated metadata."""

    @abstractmethod
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
        """Record model generation telemetry including token usage and cost."""

    @abstractmethod
    def record_score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> None:
        """Attach an evaluation or quality score to a trace."""

    @abstractmethod
    def flush(self) -> None:
        """Flush pending spans and generation records to the backend."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release observability resources and ensure all events are persisted."""


class NoOpTracingPort(TracingPort):
    """Default no-op implementation of TracingPort for testing or unconfigured runs."""

    def start_trace(
        self,
        run_id: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> TraceContext:
        return TraceContext(trace_id=run_id, run_id=run_id, name=name)

    def start_span(
        self,
        trace_id: str,
        name: str,
        parent_span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SpanContext:
        return SpanContext(
            span_id=f"noop-span-{name}",
            trace_id=trace_id,
            name=name,
            parent_span_id=parent_span_id,
        )

    def end_span(
        self,
        span: SpanContext,
        status: str = "success",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        pass

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
        pass

    def record_score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> None:
        pass

    def flush(self) -> None:
        pass

    def shutdown(self) -> None:
        pass
