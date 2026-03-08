"""Artifact CRUD endpoints.

Provides:
    GET    /artifacts              – list artifacts (filter by thread_id, type)
    POST   /artifacts              – create an artifact
    GET    /artifacts/{id}         – get a single artifact
    PATCH  /artifacts/{id}         – partial update
    DELETE /artifacts/{id}         – delete an artifact
    GET    /artifacts/{id}/download – download artifact content as file
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user
from services.artifact_service import ArtifactService
from models.user import User
from schemas.artifact import ArtifactCreate, ArtifactUpdate, ArtifactInDB

router = APIRouter(prefix="/artifacts", tags=["artifacts"])

_svc = ArtifactService()

# MIME types for download
_MIME_MAP = {
    "code": "text/plain",
    "document": "text/markdown",
    "data": "application/json",
    "image": "application/octet-stream",
}


# -- List --

@router.get("", response_model=List[ArtifactInDB])
async def list_artifacts(
    thread_id: Optional[UUID] = Query(None),
    artifact_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
):
    """List artifacts for the authenticated user."""
    return await concurrency_manager.run_in_thread(
        _svc.list_artifacts,
        user.id,
        thread_id=thread_id,
        artifact_type=artifact_type,
        limit=limit,
        offset=offset,
    )


# -- Create --

@router.post("", response_model=ArtifactInDB, status_code=status.HTTP_201_CREATED)
async def create_artifact(
    body: ArtifactCreate,
    user: User = Depends(get_current_user),
):
    """Create a new artifact."""
    return await concurrency_manager.run_in_thread(_svc.create_artifact, user.id, body)


# -- Get --

@router.get("/{artifact_id}", response_model=ArtifactInDB)
async def get_artifact(
    artifact_id: UUID,
    user: User = Depends(get_current_user),
):
    """Get a single artifact by ID."""
    a = await concurrency_manager.run_in_thread(_svc.get_artifact, user.id, artifact_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found")
    return a


# -- Update --

@router.patch("/{artifact_id}", response_model=ArtifactInDB)
async def update_artifact(
    artifact_id: UUID,
    body: ArtifactUpdate,
    user: User = Depends(get_current_user),
):
    """Partially update an artifact."""
    a = await concurrency_manager.run_in_thread(_svc.update_artifact, user.id, artifact_id, body)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found")
    return a


# -- Delete --

@router.delete("/{artifact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_artifact(
    artifact_id: UUID,
    user: User = Depends(get_current_user),
):
    """Delete an artifact."""
    deleted = await concurrency_manager.run_in_thread(_svc.delete_artifact, user.id, artifact_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found")


# -- Download --

@router.get("/{artifact_id}/download")
async def download_artifact(
    artifact_id: UUID,
    user: User = Depends(get_current_user),
):
    """Download artifact content as a file."""
    a = await concurrency_manager.run_in_thread(_svc.get_artifact, user.id, artifact_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found")

    content_type = _MIME_MAP.get(a.artifact_type, "application/octet-stream")
    return Response(
        content=a.content.encode("utf-8"),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{a.name}"',
        },
    )
