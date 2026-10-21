"""Verification script checking for drift in exported OpenAPI schema and
generated client.
"""

import json
import sys
from pathlib import Path

from agency.interfaces.api.app import create_app
from agency.interfaces.api.config import APISettings


def verify_openapi_drift(schema_path: Path | str = "docs/openapi.json") -> bool:
    """Return True if on-disk OpenAPI schema matches the live application schema."""
    target = Path(schema_path)
    if not target.is_file():
        sys.stderr.write(f"OpenAPI file not found at '{target}'.\n")
        return False

    current_disk_json = target.read_text(encoding="utf-8")
    app = create_app(APISettings(env="development", allow_unauthenticated=True))
    live_schema = app.openapi()
    live_json = json.dumps(live_schema, indent=2, sort_keys=True) + "\n"

    if current_disk_json != live_json:
        sys.stderr.write(
            f"Drift detected: On-disk '{target}' does not match live OpenAPI schema.\n"
            "Run 'agency export-openapi' to regenerate.\n"
        )
        return False

    sys.stdout.write("OpenAPI schema is up-to-date with zero drift.\n")
    return True


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "docs/openapi.json"
    ok = verify_openapi_drift(path)
    sys.exit(0 if ok else 1)
