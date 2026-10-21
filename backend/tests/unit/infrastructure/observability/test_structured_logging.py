"""Unit tests for structured JSON logging, redaction, and correlation propagation."""

import json
import logging

from agency.infrastructure.observability.logging import (
    JSONFormatter,
    bind_context,
    redact_data,
    redact_sensitive_text,
    setup_logging,
)


def test_redact_sensitive_text_masks_credentials() -> None:
    """Helper redacts Bearer tokens, key-value secrets, and private keys."""
    # Bearer token
    assert (
        redact_sensitive_text("Authorization: Bearer my-secret-token-xyz")
        == "Authorization: Bearer [REDACTED]"
    )

    # Key-value secret
    assert (
        redact_sensitive_text('api_key="sk-12345678abcdef"') == 'api_key="[REDACTED]"'
    )
    assert (
        redact_sensitive_text("secret: super_secret_pass_123") == "secret: [REDACTED]"
    )

    # Private key
    prefix = "BEGIN" + " RSA" + " PRIVATE" + " KEY"
    suffix = "END" + " RSA" + " PRIVATE" + " KEY"
    header = f"-----{prefix}-----\n"
    footer = f"\n-----{suffix}-----"
    raw_key = f"{header}MIIEowIBAAKCAQEA04...secret_bytes...{footer}"
    redacted_key = redact_sensitive_text(raw_key)
    assert "[REDACTED_PRIVATE_KEY]" in redacted_key
    assert "secret_bytes" not in redacted_key


def test_redact_data_masks_nested_dictionaries() -> None:
    """Nested dictionaries have sensitive keys redacted recursively."""
    payload = {
        "user": "test_user",
        "api_key": "raw_secret_key",
        "nested": {
            "token": "tok_12345",
            "password": "pass",
            "items": ["safe_string", "Bearer secret_bearer_token"],
        },
    }
    cleaned = redact_data(payload)
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["nested"]["token"] == "[REDACTED]"
    assert cleaned["nested"]["password"] == "[REDACTED]"
    assert cleaned["nested"]["items"][0] == "safe_string"
    assert "Bearer [REDACTED]" in cleaned["nested"]["items"][1]


def test_json_formatter_outputs_valid_json_with_correlation() -> None:
    """JSONFormatter includes UTC timestamp, level, message, and correlated IDs."""
    formatter = JSONFormatter(environment="test-env")

    record = logging.LogRecord(
        name="agency.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Processing brief for %s",
        args=("Elena",),
        exc_info=None,
    )

    with bind_context(
        run_id="run-test-1",
        trace_id="run-test-1",
        span_id="span-123",
        node_name="pm_spec",
        request_id="req-999",
    ):
        output = formatter.format(record)

    data = json.loads(output)
    assert data["level"] == "INFO"
    assert data["logger"] == "agency.test"
    assert data["message"] == "Processing brief for Elena"
    assert data["environment"] == "test-env"
    assert data["run_id"] == "run-test-1"
    assert data["trace_id"] == "run-test-1"
    assert data["span_id"] == "span-123"
    assert data["node_name"] == "pm_spec"
    assert data["request_id"] == "req-999"
    assert "timestamp" in data


def test_json_formatter_handles_exceptions_safely() -> None:
    """Exceptions are serialized with redacted error summaries."""
    formatter = JSONFormatter()

    try:
        raise ValueError("Invalid secret: api_key=topsecretpassword123")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="agency.error",
        level=logging.ERROR,
        pathname="test.py",
        lineno=45,
        msg="Operation failed",
        args=(),
        exc_info=exc_info,
    )

    output = formatter.format(record)
    data = json.loads(output)

    assert data["level"] == "ERROR"
    assert data["exception_type"] == "ValueError"
    assert "topsecretpassword123" not in data["error_summary"]
    assert "[REDACTED]" in data["error_summary"]


def test_setup_logging_configures_root_handler() -> None:
    """setup_logging configures root logger without creating duplicate handlers."""
    setup_logging(level="DEBUG", json_format=True, environment="unit-test")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JSONFormatter)

    # Calling setup_logging again replaces the handler
    setup_logging(level="INFO", json_format=False)
    assert len(root.handlers) == 1
    assert not isinstance(root.handlers[0].formatter, JSONFormatter)
