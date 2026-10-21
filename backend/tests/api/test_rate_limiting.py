"""API tests for rate limiting, body size limits, and request correlation middleware."""

from fastapi.testclient import TestClient

from tests.api.conftest import APITestHarness


def test_rate_limiting_create_runs_enforced(
    client: TestClient, harness: APITestHarness
) -> None:
    """Sending requests faster than permitted limit triggers 429 RATE_LIMIT_EXCEEDED."""
    payload = {
        "brief": {
            "client_name": "Elena",
            "site_type": "Portfolio",
            "pages": ["Home"],
            "tone": "Refined",
            "content_notes": "Notes",
        }
    }

    # Limit is 10 per minute in harness settings
    for _ in range(10):
        res = client.post("/api/v1/runs", json=payload)
        assert res.status_code == 202

    # 11th request must be rejected with 429
    res_exceeded = client.post("/api/v1/runs", json=payload)
    assert res_exceeded.status_code == 429

    data = res_exceeded.json()
    assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Rate limit" in data["error"]["message"]


def test_request_size_limit_middleware_blocks_oversized_payloads(
    client: TestClient,
) -> None:
    """Request with body exceeding max size returns 413 REQUEST_TOO_LARGE."""
    oversized_body = "x" * (1048576 + 500)
    response = client.post(
        "/api/v1/runs",
        content=oversized_body,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413

    data = response.json()
    assert data["error"]["code"] == "REQUEST_TOO_LARGE"
    assert "exceeds maximum limit" in data["error"]["message"]


def test_request_id_generated_and_echoed(client: TestClient) -> None:
    """When X-Request-ID is omitted, server generates and returns correlation ID."""
    response = client.get("/health")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) >= 16


def test_request_id_valid_incoming_preserved(client: TestClient) -> None:
    """Valid alphanumeric client-supplied X-Request-ID is preserved in response."""
    custom_id = "client-req-abc-123_456"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_request_id_malformed_incoming_replaced_with_safe_id(
    client: TestClient,
) -> None:
    """Malformed or injected X-Request-ID header is replaced with safe UUID."""
    malicious_id = "invalid\r\nInjected-Header: evil\x00"
    response = client.get("/health", headers={"X-Request-ID": malicious_id})
    assert response.status_code == 200
    returned_id = response.headers.get("X-Request-ID")
    assert returned_id != malicious_id
    assert returned_id is not None
    assert "\r" not in returned_id
    assert "\n" not in returned_id
