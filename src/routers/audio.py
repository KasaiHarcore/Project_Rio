"""Audio overview endpoints.

Provides:
    GET    /audio            – list audio overviews
    GET    /audio/{id}       – get audio overview metadata
    GET    /audio/{id}/stream – stream audio file
    POST   /audio/generate   – start audio generation
    DELETE /audio/{id}       – delete audio overview
"""

from __future__ import annotations

import os
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_audio_service
from core.exceptions import NotFoundError
from models.user import User
from schemas.audio_overview import AudioGenerateRequest, AudioOverviewInDB
from services.audio_service import AudioService

router = APIRouter(prefix="/audio", tags=["audio"])


@router.get("", response_model=List[AudioOverviewInDB])
async def list_overviews(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    svc: AudioService = Depends(get_audio_service),
):
    """List audio overviews for the authenticated user."""
    return await concurrency_manager.run_in_thread(
        svc.list_overviews, user.id, limit, offset,
    )


@router.get("/{overview_id}", response_model=AudioOverviewInDB)
async def get_overview(
    overview_id: UUID,
    user: User = Depends(get_current_user),
    svc: AudioService = Depends(get_audio_service),
):
    """Get audio overview metadata."""
    result = await concurrency_manager.run_in_thread(svc.get_overview, user.id, overview_id)
    if not result:
        raise NotFoundError("Audio overview not found")
    return result


@router.get("/{overview_id}/stream")
async def stream_audio(
    overview_id: UUID,
    user: User = Depends(get_current_user),
    svc: AudioService = Depends(get_audio_service),
):
    """Stream the audio file with range request support."""
    overview = await concurrency_manager.run_in_thread(svc.get_overview, user.id, overview_id)
    if not overview:
        raise NotFoundError("Audio overview not found")
    if not overview.audio_path or not os.path.exists(overview.audio_path):
        raise NotFoundError("Audio file not available")

    # Determine media type and filename
    ext = os.path.splitext(overview.audio_path)[1].lower()
    media_types = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg"}
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=overview.audio_path,
        media_type=media_type,
        filename=f"{overview.title}{ext}",
    )


@router.post("/generate", response_model=AudioOverviewInDB, status_code=status.HTTP_202_ACCEPTED)
async def generate_audio(
    body: AudioGenerateRequest,
    user: User = Depends(get_current_user),
    svc: AudioService = Depends(get_audio_service),
):
    """Start audio overview generation (async).

    Returns immediately with status=pending. Poll GET /audio/{id} for status updates.
    """
    return await concurrency_manager.run_in_thread(svc.create_overview, user.id, body)


@router.delete("/{overview_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_overview(
    overview_id: UUID,
    user: User = Depends(get_current_user),
    svc: AudioService = Depends(get_audio_service),
):
    """Delete an audio overview and its audio file."""
    ok = await concurrency_manager.run_in_thread(svc.delete_overview, user.id, overview_id)
    if not ok:
        raise NotFoundError("Audio overview not found")
