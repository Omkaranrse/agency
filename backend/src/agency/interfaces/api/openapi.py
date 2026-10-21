"""Deterministic OpenAPI schema exporter for Agency API."""

import json
import sys
from pathlib import Path

from agency.interfaces.api.app import create_app
from agency.interfaces.api.config import APISettings


def export_openapi_json(output_path: Path | str = "docs/openapi.json") -> str:
    """Generate and write a deterministic OpenAPI 3.1 JSON schema to disk."""
    settings = APISettings(env="development", allow_unauthenticated=True)
    app = create_app(settings)
    schema = app.openapi()

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    json_str = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    target.write_text(json_str, encoding="utf-8")
    return str(target.resolve())


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "docs/openapi.json"
    dest = export_openapi_json(out)
    print(f"OpenAPI schema successfully exported to: {dest}")
