"""API route handlers for listing and retrieving run artifacts securely."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from agency.application.ports.artifact_storage import ArtifactStoragePort
from agency.application.ports.run_repository import RunRepositoryPort
from agency.application.use_cases.get_run import GetRun
from agency.interfaces.api.dependencies import (
    get_api_key,
    get_artifact_storage,
    get_run_repository,
    limit_read_ops,
)
from agency.interfaces.api.schemas.artifacts import (
    ArtifactMetadataDTO,
    ListArtifactsResponse,
)

router = APIRouter(prefix="/runs", tags=["Artifacts"])


@router.get(
    "/{run_id}/artifacts",
    status_code=status.HTTP_200_OK,
    response_model=ListArtifactsResponse,
    dependencies=[Depends(get_api_key), Depends(limit_read_ops)],
)
async def list_run_artifacts(
    run_id: str,
    repository: Annotated[RunRepositoryPort, Depends(get_run_repository)],
    storage: Annotated[ArtifactStoragePort, Depends(get_artifact_storage)],
) -> ListArtifactsResponse:
    """List metadata for all approved artifacts produced by a run."""
    # Validate run existence
    use_case = GetRun(repository=repository)
    use_case.execute(run_id=run_id)

    raw_artifacts = storage.list_artifacts(run_id=run_id)
    items = [
        ArtifactMetadataDTO(
            artifact_id=a.artifact_id,
            run_id=a.run_id,
            artifact_type=a.artifact_type,
            display_name=a.display_name,
            mime_type=a.mime_type,
            size_bytes=a.size_bytes,
            created_at=a.created_at,
            download_available=a.download_available,
        )
        for a in raw_artifacts
    ]
    return ListArtifactsResponse(items=items, total=len(items))


@router.get(
    "/{run_id}/artifacts/{artifact_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_api_key), Depends(limit_read_ops)],
)
async def get_run_artifact(
    run_id: str,
    artifact_id: str,
    repository: Annotated[RunRepositoryPort, Depends(get_run_repository)],
    storage: Annotated[ArtifactStoragePort, Depends(get_artifact_storage)],
) -> Response:
    """Download approved artifact with safe headers and content disposition."""
    # Validate run existence
    use_case = GetRun(repository=repository)
    use_case.execute(run_id=run_id)

    meta, content = storage.get_artifact(run_id=run_id, artifact_id=artifact_id)

    clean_name = meta.display_name.replace('"', "").replace("\n", "")
    safe_filename = clean_name.replace("\r", "")

    return Response(
        content=content,
        media_type=meta.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=3600",
        },
    )
