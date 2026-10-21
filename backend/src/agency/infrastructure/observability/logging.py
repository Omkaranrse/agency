"""Structured JSON logging with correlation IDs, redaction, and context binding."""

import json
import logging
import os
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Thread-local/asyncio context variables for distributed correlation
current_run_id: ContextVar[str | None] = ContextVar("current_run_id", default=None)
current_trace_id: ContextVar[str | None] = ContextVar("current_trace_id", default=None)
current_span_id: ContextVar[str | None] = ContextVar("current_span_id", default=None)
current_node_name: ContextVar[str | None] = ContextVar(
    "current_node_name", default=None
)
current_request_id: ContextVar[str | None] = ContextVar(
    "current_request_id", default=None
)

SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "secret",
    "token",
    "authorization",
    "password",
    "private_key",
    "credentials",
    "gemini_api_key",
    "openai_api_key",
    "anthropic_api_key",
}

# Regex patterns for redaction
_BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9_\-\.]+")
_KEY_VALUE_PATTERN = re.compile(
    r'(?i)(["\']?(?:api[_-]?key|secret|token|password|auth|authorization)["\']?\s*[:=]\s*(?:Bearer\s+)?["\']?)([^"\'\s,;\[]{6,})(["\']?)'
)
_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----",
    re.DOTALL,
)


def redact_sensitive_text(text: str) -> str:
    """Redact sensitive credentials, authorization tokens, and keys from text."""
    if not text:
        return text

    # Redact private keys
    text = _PRIVATE_KEY_PATTERN.sub("[REDACTED_PRIVATE_KEY]", text)

    # Redact key-value pairs
    def _kv_replace(match: re.Match[str]) -> str:
        prefix, _secret, suffix = match.groups()
        if "bearer" in prefix.lower():
            clean_prefix = re.sub(r"(?i)bearer\s*$", "Bearer ", prefix)
            return f"{clean_prefix}[REDACTED]{suffix}"
        return f"{prefix}[REDACTED]{suffix}"

    text = _KEY_VALUE_PATTERN.sub(_kv_replace, text)

    # Redact standalone Bearer tokens
    def _bearer_replace(match: re.Match[str]) -> str:
        val = match.group(0)
        if "[REDACTED]" in val:
            return val
        return "Bearer [REDACTED]"

    text = _BEARER_PATTERN.sub(_bearer_replace, text)
    return text


def redact_data(obj: Any) -> Any:
    """Recursively redact sensitive dictionary keys and values."""
    if isinstance(obj, dict):
        clean: dict[str, Any] = {}
        for k, v in obj.items():
            if any(s in str(k).lower() for s in SENSITIVE_KEYS):
                clean[k] = "[REDACTED]"
            else:
                clean[k] = redact_data(v)
        return clean
    if isinstance(obj, list | tuple):
        return [redact_data(item) for item in obj]
    if isinstance(obj, str):
        return redact_sensitive_text(obj)
    return obj


@contextmanager
def bind_context(
    run_id: str | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
    node_name: str | None = None,
    request_id: str | None = None,
) -> Iterator[None]:
    """Context manager to bind correlation identifiers for the duration of a block."""
    tokens = []
    if run_id is not None:
        tokens.append((current_run_id, current_run_id.set(run_id)))
    if trace_id is not None:
        tokens.append((current_trace_id, current_trace_id.set(trace_id)))
    if span_id is not None:
        tokens.append((current_span_id, current_span_id.set(span_id)))
    if node_name is not None:
        tokens.append((current_node_name, current_node_name.set(node_name)))
    if request_id is not None:
        tokens.append((current_request_id, current_request_id.set(request_id)))

    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


class JSONFormatter(logging.Formatter):
    """Structured JSON formatter outputting correlated log records."""

    def __init__(self, environment: str | None = None) -> None:
        super().__init__()
        self.environment = environment or os.getenv(
            "AGENCY_ENV", os.getenv("APP_ENV", "development")
        )

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a LogRecord into a redacted, correlated JSON line."""
        timestamp = datetime.now(UTC).isoformat()
        message = redact_sensitive_text(record.getMessage())

        # Extract correlation IDs from record attributes or contextvars
        run_id = getattr(record, "run_id", None) or current_run_id.get(None)
        trace_id = getattr(record, "trace_id", None) or current_trace_id.get(None)
        span_id = getattr(record, "span_id", None) or current_span_id.get(None)
        node_name = getattr(record, "node_name", None) or current_node_name.get(None)
        request_id = getattr(record, "request_id", None) or current_request_id.get(None)

        log_payload: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "environment": self.environment,
        }

        if run_id is not None:
            log_payload["run_id"] = run_id
        if trace_id is not None:
            log_payload["trace_id"] = trace_id
        if span_id is not None:
            log_payload["span_id"] = span_id
        if node_name is not None:
            log_payload["node_name"] = node_name
        if request_id is not None:
            log_payload["request_id"] = request_id

        # Safe exception serialization
        if record.exc_info and record.exc_info[1]:
            exc_type = (
                record.exc_info[0].__name__
                if record.exc_info[0] is not None
                else "Exception"
            )
            raw_summary = str(record.exc_info[1])
            log_payload["exception_type"] = exc_type
            log_payload["error_summary"] = redact_sensitive_text(raw_summary)

        # Append any extra fields added via logger.*(..., extra={...})
        standard_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "run_id",
            "trace_id",
            "span_id",
            "node_name",
            "request_id",
        }
        for attr, val in record.__dict__.items():
            if attr not in standard_attrs and not attr.startswith("_"):
                log_payload[attr] = redact_data(val)

        return json.dumps(log_payload, default=str)


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    environment: str | None = None,
) -> None:
    """Centralized configuration for standard output logging."""
    root_logger = logging.getLogger()
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if json_format:
        handler.setFormatter(JSONFormatter(environment=environment))
    else:
        plain_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
        handler.setFormatter(logging.Formatter(plain_format))

    root_logger.addHandler(handler)
