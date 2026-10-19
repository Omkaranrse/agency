"""Configuration and state models for the Docker sandbox adapter."""

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class SandboxConfig(BaseModel):
    """Configuration governing Docker container isolation and resource boundaries."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    image: str = "agency-sandbox:latest"
    base_workspace_dir: Path | None = None
    nano_cpus: int = 1_000_000_000  # 1.0 CPU
    mem_limit: str = "512m"
    pids_limit: int = 100
    command_timeout: int = 60
    max_container_lifetime: int = 600
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    max_output_bytes: int = 1 * 1024 * 1024  # 1 MB
    user: str = "1000:1000"
    cap_drop: list[str] = Field(default_factory=lambda: ["ALL"])
    security_opt: list[str] = Field(default_factory=lambda: ["no-new-privileges:true"])
    network_mode: str = "none"
    container_workspace_dir: str = "/workspace"


class SandboxContainerInfo(BaseModel):
    """Metadata tracking an active containerized sandbox."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    sandbox_id: str
    container_id: str
    host_workspace_path: Path
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    timeout_seconds: int = 300
    is_destroyed: bool = False


__all__ = [
    "SandboxConfig",
    "SandboxContainerInfo",
]
