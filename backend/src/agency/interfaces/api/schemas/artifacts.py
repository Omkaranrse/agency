"""Artifact schemas for artifact listing and retrieval endpoints."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ArtifactMetadataDTO(BaseModel):
    """Safe metadata describing an available run artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: str = Field(description="Unique artifact identifier")
    run_id: str = Field(description="Associated run identifier")
    artifact_type: str = Field(description="Approved category of artifact")
    display_name: str = Field(description="User-facing artifact filename")
    mime_type: str = Field(description="Content MIME type")
    size_bytes: int | None = Field(default=None, description="Size in bytes")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    download_available: bool = Field(
        default=True, description="True if raw file can be downloaded"
    )


class ListArtifactsResponse(BaseModel):
    """Collection response containing artifact metadata for a run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: list[ArtifactMetadataDTO]
    total: int = Field(ge=0)
