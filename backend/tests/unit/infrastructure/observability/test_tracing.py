"""Unit tests for tracing adapters, trace context, and metadata sanitization."""

from unittest.mock import MagicMock

from tests.fakes.fake_tracing import FakeTracing

from agency.application.ports.tracing import SpanContext, TraceContext
from agency.infrastructure.observability.config import ObservabilityConfig
from agency.infrastructure.observability.langfuse_adapter import (
    LangfuseAdapter,
    _sanitize_metadata,
)
from agency.infrastructure.observability.noop_adapter import NoOpTracingAdapter


def test_noop_tracing_adapter_operations() -> None:
    """NoOpTracingAdapter executes all methods silently without errors."""
    adapter = NoOpTracingAdapter()

    trace = adapter.start_trace(
        run_id="run-123", name="test-run", metadata={"env": "test"}
    )
    assert isinstance(trace, TraceContext)
    assert trace.run_id == "run-123"

    span = adapter.start_span(
        trace_id=trace.trace_id, name="node.build", metadata={"key": "val"}
    )
    assert isinstance(span, SpanContext)
    assert span.trace_id == trace.trace_id
    assert span.name == "node.build"

    adapter.end_span(span, status="success")
    adapter.record_generation(
        trace_id=trace.trace_id,
        span_id=span.span_id,
        name="pm_gen",
        model="fake-model",
        input_tokens=100,
        output_tokens=50,
        cost=0.001,
    )
    adapter.record_score(
        trace_id=trace.trace_id, name="qa_score", value=1.0, comment="All passed"
    )
    adapter.flush()
    adapter.shutdown()


def test_fake_tracing_records_telemetry() -> None:
    """FakeTracing test double records traces, spans, generations, and scores."""
    fake = FakeTracing()
    assert not fake.has_trace("run-abc")

    fake.start_trace("run-abc", name="agency.workflow")
    assert fake.has_trace("run-abc")

    span = fake.start_span("run-abc", name="node.intake")
    assert len(fake.spans) == 1
    assert fake.spans[0].name == "node.intake"

    fake.end_span(span, status="success")
    assert len(fake.ended_spans) == 1
    assert fake.ended_spans[0].status == "success"

    fake.record_generation(
        trace_id="run-abc",
        span_id=span.span_id,
        name="test_call",
        model="gemini-1.5-pro",
        input_tokens=200,
        output_tokens=80,
    )
    assert len(fake.generations) == 1
    assert fake.generations[0].input_tokens == 200

    fake.record_score("run-abc", "qa_pass", 1.0)
    assert len(fake.scores) == 1
    assert fake.scores[0].name == "qa_pass"

    fake.clear()
    assert len(fake.traces) == 0
    assert len(fake.spans) == 0


def test_metadata_sanitization_removes_secrets() -> None:
    """Sanitizer redacts keys containing api_key, token, password, and private_key."""
    raw = {
        "user_id": "usr_123",
        "api_key": "sk-secret-token-12345",
        "nested": {
            "oauth_token": "bearer-token-abc",
            "password": "super-secret-pwd",
            "safe_count": 42,
        },
        "safe_flag": True,
    }
    clean = _sanitize_metadata(raw)

    assert clean["user_id"] == "usr_123"
    assert clean["api_key"] == "[REDACTED]"
    assert clean["nested"]["oauth_token"] == "[REDACTED]"
    assert clean["nested"]["password"] == "[REDACTED]"
    assert clean["nested"]["safe_count"] == 42
    assert clean["safe_flag"] is True


def test_langfuse_adapter_unconfigured_falls_back_safely() -> None:
    """LangfuseAdapter behaves safely when credentials are empty or disabled."""
    config = ObservabilityConfig(
        enabled=False,
        public_key=None,
        secret_key=None,
    )
    adapter = LangfuseAdapter(config=config)
    assert adapter._client is None

    trace = adapter.start_trace("run-xyz", "test-run")
    assert trace.run_id == "run-xyz"

    span = adapter.start_span(trace.trace_id, "node.qa")
    assert span.trace_id == trace.trace_id

    # Should not raise exception
    adapter.end_span(span, status="success")
    adapter.record_generation(trace.trace_id, span.span_id, "gen", "model", 10, 20)
    adapter.record_score(trace.trace_id, "qa", 1.0)
    adapter.flush()
    adapter.shutdown()


def test_langfuse_adapter_exception_resilience() -> None:
    """Exceptions from Langfuse client are trapped without crashing workflow."""
    config = ObservabilityConfig(
        enabled=True,
        public_key="pk-test",
        secret_key="sk-test",
        host="http://localhost:3000",
    )
    adapter = LangfuseAdapter(config=config)

    # Mock internal client to raise an exception
    mock_client = MagicMock()
    mock_client.trace.side_effect = ConnectionError("Langfuse server unreachable")
    mock_client.span.side_effect = ConnectionError("Langfuse server unreachable")
    mock_client.flush.side_effect = ConnectionError("Langfuse server unreachable")
    adapter._client = mock_client

    # None of these should raise an exception
    trace = adapter.start_trace("run-err", "test-run")
    assert trace.run_id == "run-err"

    span = adapter.start_span(trace.trace_id, "test-span")
    adapter.end_span(span)
    adapter.record_generation(trace.trace_id, span.span_id, "gen", "mod", 1, 1)
    adapter.record_score(trace.trace_id, "score", 0.5)
    adapter.flush()
    adapter.shutdown()
