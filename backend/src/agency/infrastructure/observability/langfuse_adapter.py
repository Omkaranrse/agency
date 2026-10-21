"""Langfuse implementation of TracingPort for distributed tracing and evaluation."""

import logging
import uuid
from typing import Any

from agency.application.ports.tracing import (
    SpanContext,
    TraceContext,
    TracingPort,
)
from agency.infrastructure.observability.config import ObservabilityConfig

logger = logging.getLogger(__name__)


def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Sanitize metadata dictionary, removing sensitive tokens and secrets."""
    if not metadata:
        return {}
    clean: dict[str, Any] = {}
    sensitive_keys = {
        "api_key",
        "secret",
        "token",
        "authorization",
        "password",
        "private_key",
    }
    for k, v in metadata.items():
        if any(s in k.lower() for s in sensitive_keys):
            clean[k] = "[REDACTED]"
        elif isinstance(v, dict):
            clean[k] = _sanitize_metadata(v)
        elif isinstance(v, str | int | float | bool) or v is None:
            clean[k] = v
        else:
            clean[k] = str(v)
    return clean


class LangfuseAdapter(TracingPort):
    """Adapter sending traces, spans, and telemetry to Langfuse."""

    def __init__(self, config: ObservabilityConfig | None = None) -> None:
        self.config = config or ObservabilityConfig()
        self._client: Any = None
        self._active_spans: dict[str, Any] = {}

        if self.config.is_configured:
            try:
                from langfuse import Langfuse

                self._client = Langfuse(
                    public_key=self.config.public_key,
                    secret_key=self.config.secret_key,
                    host=self.config.host,
                    release=self.config.release,
                    debug=self.config.debug,
                )
                logger.info(
                    "Langfuse client initialized (host=%s, env=%s).",
                    self.config.host,
                    self.config.environment,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to initialize Langfuse client: %s. Tracing disabled.",
                    exc,
                )
                self._client = None
        else:
            logger.debug("Langfuse observability unconfigured; using no-op fallback.")

    def start_trace(
        self,
        run_id: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> TraceContext:
        """Create or reference a root trace correlated with the application run ID."""
        trace_context = TraceContext(
            trace_id=run_id,
            run_id=run_id,
            name=name,
        )

        if not self._client:
            return trace_context

        try:
            safe_meta = _sanitize_metadata(metadata)
            safe_meta["environment"] = self.config.environment
            safe_meta["run_id"] = run_id

            self._client.trace(
                id=run_id,
                name=name,
                metadata=safe_meta,
                tags=[self.config.environment, name],
            )
        except Exception as exc:
            logger.warning(
                "Error creating Langfuse trace for run '%s': %s", run_id, exc
            )

        return trace_context

    def start_span(
        self,
        trace_id: str,
        name: str,
        parent_span_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SpanContext:
        """Create a child span within an active trace."""
        span_id = f"span-{uuid.uuid4().hex[:12]}"
        span_context = SpanContext(
            span_id=span_id,
            trace_id=trace_id,
            name=name,
            parent_span_id=parent_span_id,
        )

        if not self._client:
            return span_context

        try:
            safe_meta = _sanitize_metadata(metadata)
            safe_meta["span_id"] = span_id

            span_obj = self._client.span(
                id=span_id,
                trace_id=trace_id,
                parent_observation_id=parent_span_id,
                name=name,
                metadata=safe_meta,
            )
            self._active_spans[span_id] = span_obj
        except Exception as exc:
            logger.warning("Error creating Langfuse span '%s': %s", name, exc)

        return span_context

    def end_span(
        self,
        span: SpanContext,
        status: str = "success",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Complete a span, recording status and optional error messages."""
        if not self._client:
            return

        try:
            span_obj = self._active_spans.pop(span.span_id, None)
            if span_obj:
                safe_meta = _sanitize_metadata(metadata) if metadata else None
                level = "ERROR" if status == "error" or error else "DEFAULT"
                span_obj.end(
                    status_message=error if error else status,
                    level=level,
                    metadata=safe_meta,
                )
        except Exception as exc:
            logger.warning("Error ending Langfuse span '%s': %s", span.name, exc)

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
        """Record an LLM generation with usage telemetry and model metadata."""
        if not self._client:
            return

        try:
            safe_meta = _sanitize_metadata(metadata)
            usage_dict: dict[str, Any] = {
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
            }
            if cost is not None and cost >= 0.0:
                usage_dict["total_cost"] = cost

            self._client.generation(
                trace_id=trace_id,
                parent_observation_id=span_id,
                name=name,
                model=model,
                usage=usage_dict,
                metadata=safe_meta,
            )
        except Exception as exc:
            logger.warning("Error recording generation in Langfuse: %s", exc)

    def record_score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> None:
        """Attach a quality, QA, or evaluation score to a trace."""
        if not self._client:
            return

        try:
            self._client.score(
                trace_id=trace_id,
                name=name,
                value=float(value),
                comment=comment,
            )
        except Exception as exc:
            logger.warning("Error recording score '%s' in Langfuse: %s", name, exc)

    def flush(self) -> None:
        """Flush pending observations to Langfuse server."""
        if not self._client:
            return
        try:
            self._client.flush()
        except Exception as exc:
            logger.warning("Error flushing Langfuse client: %s", exc)

    def shutdown(self) -> None:
        """Flush observations and shutdown Langfuse thread pool."""
        if not self._client:
            return
        try:
            self._client.flush()
            self._client.shutdown()
        except Exception as exc:
            logger.warning("Error shutting down Langfuse client: %s", exc)
