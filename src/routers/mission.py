"""Mission CRUD endpoints.

Provides:
    GET    /missions         – list all missions (with optional filters)
    GET    /missions/stats   – aggregate mission stats
    GET    /missions/{id}    – get a single mission
    POST   /missions         – create a mission manually
    PATCH  /missions/{id}    – partial update
    PATCH  /missions/{id}/steps/{idx}/toggle  – toggle one step
    DELETE /missions/{id}    – delete a mission
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.dependencies import get_current_user, get_db
from services.mission_service import MissionService
from models.mission import MissionStatus, MissionPriority
from models.user import User
from schemas.mission import MissionCreate, MissionUpdate, MissionInDB

router = APIRouter(prefix="/missions", tags=["missions"])

_svc = MissionService()


# ── List ────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[MissionInDB])
def list_missions(
    status_filter: Optional[MissionStatus] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    priority: Optional[MissionPriority] = Query(None),
    overdue: bool = Query(False),
    deadline_before: Optional[datetime] = Query(None),
    deadline_after: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
):
    """List missions for the authenticated user with optional filters."""
    return _svc.list_missions(
        user.id,
        status=status_filter,
        category=category,
        priority=priority,
        overdue_only=overdue,
        deadline_before=deadline_before,
        deadline_after=deadline_after,
        limit=limit,
        offset=offset,
    )


# ── Stats ───────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_mission_stats(user: User = Depends(get_current_user)):
    """Return aggregate mission counts (total, active, completed)."""
    return _svc.get_stats(user.id)


# ── Get one ─────────────────────────────────────────────────────────────────

@router.get("/{mission_id}", response_model=MissionInDB)
def get_mission(
    mission_id: UUID,
    user: User = Depends(get_current_user),
):
    """Get a single mission by ID."""
    m = _svc.get_mission(user.id, mission_id)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission not found")
    return m


# ── Create ──────────────────────────────────────────────────────────────────

@router.post("", response_model=MissionInDB, status_code=status.HTTP_201_CREATED)
def create_mission(
    body: MissionCreate,
    user: User = Depends(get_current_user),
):
    """Create a new mission."""
    return _svc.create_mission(user.id, body)


# ── Update ──────────────────────────────────────────────────────────────────

@router.patch("/{mission_id}", response_model=MissionInDB)
def update_mission(
    mission_id: UUID,
    body: MissionUpdate,
    user: User = Depends(get_current_user),
):
    """Partially update a mission."""
    m = _svc.update_mission(user.id, mission_id, body)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission not found")
    return m


# ── Toggle step ─────────────────────────────────────────────────────────────

@router.patch("/{mission_id}/steps/{step_index}/toggle", response_model=MissionInDB)
def toggle_mission_step(
    mission_id: UUID,
    step_index: int,
    user: User = Depends(get_current_user),
):
    """Toggle the done status of a single step."""
    m = _svc.toggle_step(user.id, mission_id, step_index)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission or step not found")
    return m


# ── Delete ──────────────────────────────────────────────────────────────────

@router.delete("/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mission(
    mission_id: UUID,
    user: User = Depends(get_current_user),
):
    """Delete a mission."""
    deleted = _svc.delete_mission(user.id, mission_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mission not found")
