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


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_openapi_schema_has_zero_drift() -> None:
    """Verify that on-disk docs/openapi.json has zero drift against app."""
    schema_path = REPO_ROOT / "docs" / "openapi.json"
    assert verify_openapi_drift(schema_path) is True


def test_generated_typescript_client_compiles() -> None:
    """Verify dashboard TypeScript client compiles with strict mode."""
    tsc_candidates = [
        REPO_ROOT / "dashboard" / "node_modules" / ".bin" / "tsc",
        REPO_ROOT / "templates" / "site-astro" / "node_modules" / ".bin" / "tsc",
    ]
    tsc_binary = None
    for cand in tsc_candidates:
        if cand.is_file():
            tsc_binary = cand
            break

    if tsc_binary is None:
        import shutil

        which_tsc = shutil.which("tsc")
        if which_tsc:
            tsc_binary = Path(which_tsc)

    assert (
        tsc_binary is not None
    ), "TypeScript compiler (tsc) not found in node_modules or PATH"
    cmd = [
        str(tsc_binary),
        "--project",
        str(REPO_ROOT / "dashboard" / "tsconfig.json"),
    ]
    res = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    err = f"TypeScript compilation failed: {res.stdout}\n{res.stderr}"
    assert res.returncode == 0, err
