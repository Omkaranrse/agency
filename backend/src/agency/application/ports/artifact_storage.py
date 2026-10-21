"""ArtifactStoragePort definition for managing and retrieving run artifacts."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ArtifactMetadata(BaseModel):
    """Metadata describing a stored run artifact."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    artifact_id: str = Field(min_length=1, max_length=100)
    run_id: str = Field(min_length=1, max_length=100)
    artifact_type: str = Field(min_length=1, max_length=50)
    display_name: str = Field(min_length=1, max_length=150)
    mime_type: str = Field(min_length=1, max_length=100)
    size_bytes: int | None = Field(default=None, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    download_available: bool = True


class ArtifactStoragePort(ABC):
    """Abstract port defining safe artifact listing and retrieval boundaries."""

    @abstractmethod
    def list_artifacts(self, run_id: str) -> list[ArtifactMetadata]:
        """List all artifacts associated with a run.

        Raises:
            ArtifactError: If artifact retrieval fails.
        """

    @abstractmethod
    def get_artifact(
        self, run_id: str, artifact_id: str
    ) -> tuple[ArtifactMetadata, bytes]:
        """Retrieve artifact metadata and raw bytes by ID for a run.

        Raises:
            ArtifactNotFoundError: If artifact does not exist.
            ArtifactAccessDeniedError: If path traversal or access is forbidden.
            ArtifactError: If retrieval fails.
        """

    @abstractmethod
    def save_artifact(
        self,
        run_id: str,
        artifact_id: str,
        artifact_type: str,
        display_name: str,
        mime_type: str,
        content: bytes,
    ) -> ArtifactMetadata:
        """Store a new artifact for a given run."""
