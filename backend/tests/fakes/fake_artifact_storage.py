"""In-memory fake implementation of ArtifactStoragePort for testing."""

from datetime import UTC, datetime

from agency.application.errors import (
    ArtifactAccessDeniedError,
    ArtifactNotFoundError,
)
from agency.application.ports.artifact_storage import (
    ArtifactMetadata,
    ArtifactStoragePort,
)


class FakeArtifactStorage(ArtifactStoragePort):
    """Deterministic in-memory artifact storage fake."""

    def __init__(self) -> None:
        self._artifacts: dict[str, dict[str, tuple[ArtifactMetadata, bytes]]] = {}

    def save_artifact(
        self,
        run_id: str,
        artifact_id: str,
        artifact_type: str,
        display_name: str,
        mime_type: str,
        content: bytes,
    ) -> ArtifactMetadata:
        """Store an artifact in memory."""
        if ".." in artifact_id or "/" in artifact_id or "\\" in artifact_id:
            raise ArtifactAccessDeniedError("Path traversal rejected")

        meta = ArtifactMetadata(
            artifact_id=artifact_id,
            run_id=run_id,
            artifact_type=artifact_type,
            display_name=display_name,
            mime_type=mime_type,
            size_bytes=len(content),
            created_at=datetime.now(UTC),
            download_available=True,
        )

        if run_id not in self._artifacts:
            self._artifacts[run_id] = {}
        self._artifacts[run_id][artifact_id] = (meta, content)
        return meta

    def list_artifacts(self, run_id: str) -> list[ArtifactMetadata]:
        """List metadata for all artifacts of a run."""
        return [meta for meta, _ in self._artifacts.get(run_id, {}).values()]

    def get_artifact(
        self, run_id: str, artifact_id: str
    ) -> tuple[ArtifactMetadata, bytes]:
        """Retrieve artifact metadata and raw bytes by ID."""
        if ".." in artifact_id or "/" in artifact_id or "\\" in artifact_id:
            raise ArtifactAccessDeniedError("Path traversal rejected")

        run_artifacts = self._artifacts.get(run_id, {})
        entry = run_artifacts.get(artifact_id)
        if entry is None:
            raise ArtifactNotFoundError(run_id=run_id, artifact_id=artifact_id)
        return entry
