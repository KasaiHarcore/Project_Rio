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

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_mission_service
from core.exceptions import NotFoundError
from services.mission_service import MissionService
from models.mission import MissionStatus, MissionPriority
from models.user import User
from schemas.mission import MissionCreate, MissionUpdate, MissionInDB

router = APIRouter(prefix="/missions", tags=["missions"])



@router.get("", response_model=List[MissionInDB])
async def list_missions(
    status_filter: Optional[MissionStatus] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    priority: Optional[MissionPriority] = Query(None),
    overdue: bool = Query(False),
    deadline_before: Optional[datetime] = Query(None),
    deadline_after: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    svc: MissionService = Depends(get_mission_service),
):
    """List missions for the authenticated user with optional filters."""
    return await concurrency_manager.run_in_thread(
        svc.list_missions,
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



@router.get("/stats")
async def get_mission_stats(
    user: User = Depends(get_current_user),
    svc: MissionService = Depends(get_mission_service),
):
    """Return aggregate mission counts (total, active, completed)."""
    return await concurrency_manager.run_in_thread(svc.get_stats, user.id)



@router.get("/{mission_id}", response_model=MissionInDB)
async def get_mission(
    mission_id: UUID,
    user: User = Depends(get_current_user),
    svc: MissionService = Depends(get_mission_service),
):
    """Get a single mission by ID."""
    m = await concurrency_manager.run_in_thread(svc.get_mission, user.id, mission_id)
    if not m:
        raise NotFoundError("Mission not found")
    return m



@router.post("", response_model=MissionInDB, status_code=status.HTTP_201_CREATED)
async def create_mission(
    body: MissionCreate,
    user: User = Depends(get_current_user),
    svc: MissionService = Depends(get_mission_service),
):
    """Create a new mission."""
    result, err = await concurrency_manager.run_in_thread(svc.create_mission, user.id, body)
    if err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err.message)
    return result



@router.patch("/{mission_id}", response_model=MissionInDB)
async def update_mission(
    mission_id: UUID,
    body: MissionUpdate,
    user: User = Depends(get_current_user),
    svc: MissionService = Depends(get_mission_service),
):
    """Partially update a mission."""
    result, err = await concurrency_manager.run_in_thread(svc.update_mission, user.id, mission_id, body)
    if err:
        if err.code == "NOT_FOUND":
            raise NotFoundError(err.message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err.message)
    return result



@router.patch("/{mission_id}/steps/{step_index}/toggle", response_model=MissionInDB)
async def toggle_mission_step(
    mission_id: UUID,
    step_index: int,
    user: User = Depends(get_current_user),
    svc: MissionService = Depends(get_mission_service),
):
    """Toggle the done status of a single step."""
    result, err = await concurrency_manager.run_in_thread(svc.toggle_step, user.id, mission_id, step_index)
    if err:
        if err.code == "NOT_FOUND":
            raise NotFoundError(err.message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err.message)
    return result



@router.delete("/{mission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mission(
    mission_id: UUID,
    user: User = Depends(get_current_user),
    svc: MissionService = Depends(get_mission_service),
):
    """Delete a mission."""
    deleted, err = await concurrency_manager.run_in_thread(svc.delete_mission, user.id, mission_id)
    if err:
        if err.code == "NOT_FOUND":
            raise NotFoundError(err.message)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err.message)
    if not deleted:
        raise NotFoundError("Mission not found")
