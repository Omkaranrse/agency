"""No-op implementation of TracingPort for testing and unconfigured environments."""

from agency.application.ports.tracing import (
    NoOpTracingPort,
    SpanContext,
    TraceContext,
    TracingPort,
)


class NoOpTracingAdapter(NoOpTracingPort):
    """Silent or logging-only implementation of TracingPort."""


__all__ = [
    "NoOpTracingAdapter",
    "NoOpTracingPort",
    "SpanContext",
    "TraceContext",
    "TracingPort",
]
