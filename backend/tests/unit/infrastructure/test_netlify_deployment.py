"""Unit tests for NetlifyDeploymentAdapter."""

from unittest.mock import MagicMock

import pytest
import requests

from agency.application.errors import (
    DeployAuthenticationError,
    DeployError,
    DeployRateLimitError,
    DeployTimeoutError,
)
from agency.infrastructure.adapters.in_memory.deploy import InMemoryDeploy
from agency.infrastructure.adapters.netlify_deployment_adapter import (
    NetlifyDeploymentAdapter,
)


def test_fallback_when_token_omitted() -> None:
    fallback = InMemoryDeploy(provider="custom-local")
    adapter = NetlifyDeploymentAdapter(auth_token=None, fallback_adapter=fallback)

    deploy = adapter.deploy_staging("proj-1", "abc1234567")
    assert deploy.provider == "custom-local"
    assert "proj-1" in str(deploy.preview_url)


def test_successful_staging_deploy() -> None:
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_client.post.return_value = mock_resp

    adapter = NetlifyDeploymentAdapter(
        auth_token="secret-token",
        site_id="my-site",
        http_client=mock_client,
    )

    deploy = adapter.deploy_staging("my-site", "commit789xyz")
    assert deploy.provider == "netlify"
    assert "deploy-preview-commit7--my-site.netlify.app" in str(deploy.preview_url)
    assert deploy.production_url is None


def test_successful_production_deploy() -> None:
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_client.post.return_value = mock_resp

    adapter = NetlifyDeploymentAdapter(
        auth_token="secret-token",
        site_id="my-site",
        http_client=mock_client,
    )

    deploy = adapter.deploy_production("my-site", "prodcommit123")
    assert deploy.provider == "netlify"
    assert "my-site.netlify.app" in str(deploy.production_url)


def test_auth_failure_raises() -> None:
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 401
    mock_client.post.return_value = mock_resp

    adapter = NetlifyDeploymentAdapter(
        auth_token="bad-token",
        site_id="my-site",
        http_client=mock_client,
    )

    with pytest.raises(DeployAuthenticationError):
        adapter.deploy_staging("my-site", "commit123")


def test_rate_limit_raises() -> None:
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 429
    mock_resp.headers = {"Retry-After": "10"}
    mock_client.post.return_value = mock_resp

    adapter = NetlifyDeploymentAdapter(
        auth_token="token",
        site_id="my-site",
        http_client=mock_client,
    )

    with pytest.raises(DeployRateLimitError) as exc_info:
        adapter.deploy_staging("my-site", "commit123")
    assert exc_info.value.retry_after == 10.0


def test_timeout_raises() -> None:
    mock_client = MagicMock()
    mock_client.post.side_effect = requests.exceptions.Timeout("timed out")

    adapter = NetlifyDeploymentAdapter(
        auth_token="token",
        site_id="my-site",
        http_client=mock_client,
    )

    with pytest.raises(DeployTimeoutError):
        adapter.deploy_staging("my-site", "commit123")


def test_server_error_raises() -> None:
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 502
    mock_client.post.return_value = mock_resp

    adapter = NetlifyDeploymentAdapter(
        auth_token="token",
        site_id="my-site",
        http_client=mock_client,
    )

    with pytest.raises(DeployError):
        adapter.deploy_production("my-site", "commit123")
