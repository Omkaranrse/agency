"""Unit tests for SSRF prevention, URL validation, and network isolation policies."""

import pytest
from pydantic import HttpUrl, ValidationError

from agency.domain.entities.brief import Brief
from agency.domain.security.url_policy import (
    SSRFSecurityError,
    validate_safe_url,
)


def test_valid_public_urls() -> None:
    """Standard public HTTPS and HTTP URLs must pass validation."""
    valid_urls = [
        "https://example.com/portfolio",
        "https://github.com/developer/project",
        "http://mybrand.org/about?section=story",
        "https://cdn.photos.com/gallery/img1.jpg",
    ]
    for url in valid_urls:
        assert validate_safe_url(url) == url


@pytest.mark.parametrize(
    "blocked_url,match_msg",
    [
        ("http://127.0.0.1/admin", r"SSRF guard"),
        ("http://127.0.0.1:8080/metrics", r"SSRF guard"),
        ("http://localhost:3000/", "internal hostname"),
        ("http://localhost/api", "internal hostname"),
        ("http://169.254.169.254/latest/meta-data/", r"SSRF guard"),
        ("http://10.0.0.1/internal", r"SSRF guard"),
        ("http://172.16.0.5/api", r"SSRF guard"),
        ("http://192.168.1.1/router", r"SSRF guard"),
        ("http://[::1]/debug", r"SSRF guard"),
        ("http://0.0.0.0:8000/", r"SSRF guard"),
        ("http://metadata.google.internal/computeMetadata/v1/", "internal hostname"),
        ("http://internal.service.local/data", "internal domain suffix"),
        ("file:///etc/passwd", "Disallowed URL scheme"),
        ("gopher://127.0.0.1:70/", "Disallowed URL scheme"),
        ("ftp://ftp.example.com/files", "Disallowed URL scheme"),
        ("http://user:pass@example.com/", "user authentication are prohibited"),
    ],
)
def test_blocked_urls_raise_ssrf_error(blocked_url: str, match_msg: str) -> None:
    """Prohibited URLs must be rejected with explicit SSRF security errors."""
    with pytest.raises(SSRFSecurityError, match=match_msg):
        validate_safe_url(blocked_url)


def test_brief_rejects_ssrf_links() -> None:
    """Brief model rejects any links pointing to internal or private addresses."""
    with pytest.raises(ValidationError) as exc_info:
        Brief(
            client_name="Malicious Client",
            site_type="Portfolio",
            pages=["home", "about"],
            tone="minimal",
            content_notes="Test notes",
            links=[HttpUrl("http://169.254.169.254/latest/meta-data/")],
        )
    assert "SSRF guard" in str(exc_info.value)
