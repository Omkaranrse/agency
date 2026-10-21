"""Configuration settings for the Agency FastAPI application."""

import os
from pathlib import Path

from pydantic import BaseModel, Field


def _load_env_file() -> None:
    """Load key-value pairs from .env file into os.environ if not already present."""
    env_paths = [
        Path(".env"),
        Path("../.env"),
        Path(__file__).resolve().parents[4] / ".env",
    ]
    for env_path in env_paths:
        if env_path.is_file():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val
                break
            except Exception:
                pass


_load_env_file()


def _parse_origins(val: str | None) -> list[str]:
    if not val:
        return ["http://localhost:3000"]
    return [orig.strip() for orig in val.split(",") if orig.strip()]


class APISettings(BaseModel):
    """Validated API configuration loaded from environment or overrides."""

    env: str = Field(
        default_factory=lambda: (
            os.getenv("AGENCY_ENVIRONMENT") or os.getenv("APP_ENV") or "development"
        )
    )
    api_key: str | None = Field(
        default_factory=lambda: os.getenv("AGENCY_API_KEY") or None
    )
    allow_unauthenticated: bool = Field(
        default_factory=lambda: (
            os.getenv("AGENCY_ALLOW_UNAUTHENTICATED", "true").lower()
            in ("1", "true", "yes")
        )
    )
    dashboard_origins: list[str] = Field(
        default_factory=lambda: _parse_origins(
            os.getenv("AGENCY_DASHBOARD_ORIGINS") or os.getenv("DASHBOARD_ORIGINS")
        )
    )
    max_request_body_size: int = Field(
        default_factory=lambda: int(
            os.getenv("AGENCY_MAX_REQUEST_BODY_SIZE", "1048576")
        )
    )
    rate_limit_reads_per_minute: int = 100
    rate_limit_writes_per_minute: int = 30
    rate_limit_creates_per_minute: int = 10
    rate_limit_window_seconds: int = 60
    sse_keep_alive_seconds: float = 15.0
    artifacts_dir: str = Field(
        default_factory=lambda: os.getenv("AGENCY_ARTIFACTS_DIR", "artifacts")
    )

    @property
    def is_production(self) -> bool:
        """Return True if running in production mode."""
        return self.env.lower() in ("production", "prod")
