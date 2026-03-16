"""NoteLink CRUD endpoints.

Provides:
    POST   /note-links              – create link manually
    POST   /note-links/bulk         – bulk create
    GET    /note-links              – list (filter: note_id, target_type)
    GET    /note-links/graph        – graph visualization data
    GET    /note-links/backlinks/{note_id} – backlinks to a note
    GET    /note-links/{link_id}    – get single
    PATCH  /note-links/{link_id}    – update
    DELETE /note-links/{link_id}    – delete
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_note_link_service
from core.exceptions import NotFoundError
from models.note_link import NoteLinkTargetType
from models.user import User
from schemas.note_link import (
    NoteLinkBulkCreate,
    NoteLinkCreate,
    NoteLinkInDB,
    NoteLinkUpdate,
    NoteGraphResponse,
)
from services.note_link_service import NoteLinkService

router = APIRouter(prefix="/note-links", tags=["note-links"])


# -- Create --

@router.post("", response_model=NoteLinkInDB, status_code=status.HTTP_201_CREATED)
async def create_link(
    body: NoteLinkCreate,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Create a note link manually."""
    return await concurrency_manager.run_in_thread(svc.create_link, user.id, body)


@router.post("/bulk", response_model=List[NoteLinkInDB], status_code=status.HTTP_201_CREATED)
async def bulk_create_links(
    body: NoteLinkBulkCreate,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Bulk create note links."""
    return await concurrency_manager.run_in_thread(
        svc.create_links_bulk, user.id, body.links,
    )


# -- List --

@router.get("", response_model=List[NoteLinkInDB])
async def list_links(
    note_id: Optional[UUID] = Query(None),
    target_type: Optional[NoteLinkTargetType] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """List note links, optionally filtered by note_id and target_type."""
    return await concurrency_manager.run_in_thread(
        svc.list_links,
        user.id,
        note_id=note_id,
        target_type=target_type,
        limit=limit,
        offset=offset,
    )


# -- Graph --

@router.get("/graph", response_model=NoteGraphResponse)
async def get_graph(
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Get note graph data for visualization."""
    return await concurrency_manager.run_in_thread(svc.get_note_graph, user.id)


# -- Backlinks --

@router.get("/backlinks/{note_id}", response_model=List[NoteLinkInDB])
async def get_backlinks(
    note_id: UUID,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Get all links pointing TO a given note."""
    return await concurrency_manager.run_in_thread(
        svc.list_backlinks, user.id, note_id,
    )


# -- Get single --

@router.get("/{link_id}", response_model=NoteLinkInDB)
async def get_link(
    link_id: UUID,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Get a single note link by ID."""
    link = await concurrency_manager.run_in_thread(svc.get_link, user.id, link_id)
    if not link:
        raise NotFoundError("Note link not found")
    return link


# -- Update --

@router.patch("/{link_id}", response_model=NoteLinkInDB)
async def update_link(
    link_id: UUID,
    body: NoteLinkUpdate,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Partially update a note link."""
    link = await concurrency_manager.run_in_thread(
        svc.update_link, user.id, link_id, body,
    )
    if not link:
        raise NotFoundError("Note link not found")
    return link


# -- Delete --

@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    link_id: UUID,
    user: User = Depends(get_current_user),
    svc: NoteLinkService = Depends(get_note_link_service),
):
    """Delete a note link."""
    deleted = await concurrency_manager.run_in_thread(
        svc.delete_link, user.id, link_id,
    )
    if not deleted:
        raise NotFoundError("Note link not found")
