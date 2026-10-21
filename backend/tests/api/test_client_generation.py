"""Tests verifying OpenAPI schema export, drift verification, and TS client."""

import json
import subprocess
from pathlib import Path

from agency.interfaces.api.openapi import export_openapi_json
from agency.interfaces.api.verify_client import verify_openapi_drift


def test_openapi_export_produces_valid_schema(tmp_path: Path) -> None:
    """OpenAPI export writes a valid, complete OpenAPI 3.1 JSON schema."""
    target_file = tmp_path / "openapi.json"
    export_openapi_json(target_file)

    assert target_file.is_file()
    data = json.loads(target_file.read_text(encoding="utf-8"))

    assert "openapi" in data
    assert "paths" in data
    assert "/api/v1/runs" in data["paths"]
    assert "/api/v1/runs/{run_id}/approve" in data["paths"]
    assert "/api/v1/runs/{run_id}/revise" in data["paths"]
    assert "/api/v1/runs/{run_id}/cancel" in data["paths"]
    assert "/api/v1/runs/{run_id}/events" in data["paths"]
    assert "/api/v1/runs/{run_id}/artifacts" in data["paths"]
    assert "components" in data
    assert "schemas" in data["components"]


def test_openapi_schema_has_zero_drift() -> None:
    """Verify that on-disk docs/openapi.json has zero drift against app."""
    assert verify_openapi_drift("docs/openapi.json") is True


def test_generated_typescript_client_compiles() -> None:
    """Verify dashboard TypeScript client compiles with strict mode."""
    tsc_binary = "./templates/site-astro/node_modules/.bin/tsc"
    cmd = [tsc_binary, "--project", "dashboard/tsconfig.json"]
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    err = f"TypeScript compilation failed: {res.stdout}\n{res.stderr}"
    assert res.returncode == 0, err
