"""Local filesystem implementation of ArtifactStoragePort with path-traversal guards."""

from datetime import UTC, datetime
from pathlib import Path

from agency.application.errors import (
    ArtifactAccessDeniedError,
    ArtifactNotFoundError,
)
from agency.application.ports.artifact_storage import (
    ArtifactMetadata,
    ArtifactStoragePort,
)

# Explicitly permitted MIME types for download safety
ALLOWED_MIME_TYPES = {
    "application/json",
    "text/plain",
    "text/css",
    "text/html",
    "application/zip",
    "image/svg+xml",
    "image/png",
}


class LocalArtifactStorage(ArtifactStoragePort):
    """File-backed artifact store enforcing path isolation and strict type controls."""

    def __init__(self, base_dir: Path | str = "artifacts") -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_index: dict[str, dict[str, ArtifactMetadata]] = {}

    def _resolve_safe_path(self, run_id: str, artifact_id: str) -> Path:
        """Resolve artifact file path and ensure it remains strictly within base dir."""
        if ".." in run_id or "/" in run_id or "\\" in run_id:
            raise ArtifactAccessDeniedError(f"Invalid run ID: '{run_id}'")
        if ".." in artifact_id or "/" in artifact_id or "\\" in artifact_id:
            raise ArtifactAccessDeniedError(f"Invalid artifact ID: '{artifact_id}'")

        run_dir = (self.base_dir / run_id).resolve()
        target = (run_dir / artifact_id).resolve()

        if not str(target).startswith(str(self.base_dir)):
            raise ArtifactAccessDeniedError("Path traversal attempt detected.")
        return target

    def save_artifact(
        self,
        run_id: str,
        artifact_id: str,
        artifact_type: str,
        display_name: str,
        mime_type: str,
        content: bytes,
    ) -> ArtifactMetadata:
        """Persist an artifact file to disk and register its metadata."""
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ArtifactAccessDeniedError(f"Disallowed MIME type: '{mime_type}'")

        target_path = self._resolve_safe_path(run_id, artifact_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)

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

        if run_id not in self._metadata_index:
            self._metadata_index[run_id] = {}
        self._metadata_index[run_id][artifact_id] = meta
        return meta

    def list_artifacts(self, run_id: str) -> list[ArtifactMetadata]:
        """List all registered artifacts for a run."""
        return list(self._metadata_index.get(run_id, {}).values())

    def get_artifact(
        self, run_id: str, artifact_id: str
    ) -> tuple[ArtifactMetadata, bytes]:
        """Retrieve artifact metadata and raw bytes."""
        run_artifacts = self._metadata_index.get(run_id, {})
        meta = run_artifacts.get(artifact_id)
        if meta is None:
            raise ArtifactNotFoundError(run_id=run_id, artifact_id=artifact_id)

        target_path = self._resolve_safe_path(run_id, artifact_id)
        if not target_path.is_file():
            raise ArtifactNotFoundError(run_id=run_id, artifact_id=artifact_id)

        return meta, target_path.read_bytes()
