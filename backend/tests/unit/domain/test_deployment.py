"""Unit tests for Deployment domain entity."""

from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl, ValidationError

from agency.domain.entities.deployment import Deployment


def mutate_attr(obj: object, name: str, value: object) -> None:
    """Helper to attempt dynamic mutation on frozen objects."""
    setattr(obj, name, value)


def test_valid_preview_deployment() -> None:
    """Test valid preview/staging deployment without production URL."""
    deployment = Deployment(
        preview_url=HttpUrl("https://preview-123.agency.run"),
        provider="cloudflare",
        deployed_at=datetime.now(UTC),
    )
    assert str(deployment.preview_url) == "https://preview-123.agency.run/"
    assert deployment.production_url is None
    assert deployment.is_preview is True
    assert deployment.is_production is False
    assert deployment.provider == "cloudflare"


def test_valid_production_deployment() -> None:
    """Test valid production release deployment."""
    deployment = Deployment(
        preview_url=HttpUrl("https://preview-123.agency.run"),
        production_url=HttpUrl("https://client-domain.com"),
        provider="vercel",
        deployed_at=datetime.now(UTC),
    )
    assert deployment.is_preview is False
    assert deployment.is_production is True
    assert str(deployment.production_url) == "https://client-domain.com/"


def test_deployment_rejects_naive_timestamp() -> None:
    """Test that timezone-naive datetimes are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Deployment(
            preview_url=HttpUrl("https://preview.agency.run"),
            provider="vercel",
            deployed_at=datetime.now(),  # naive datetime
        )
    assert "timezone-aware" in str(exc_info.value)


def test_deployment_is_immutable() -> None:
    """Test that Deployment cannot be modified after construction."""
    deployment = Deployment(
        preview_url=HttpUrl("https://preview.agency.run"),
        provider="vercel",
        deployed_at=datetime.now(UTC),
    )
    with pytest.raises(ValidationError):
        mutate_attr(deployment, "provider", "aws")
