"""Automation CRUD and manual trigger endpoints.

Provides:
    GET    /automations          – list automations
    GET    /automations/{id}     – get single automation
    POST   /automations          – create automation
    PATCH  /automations/{id}     – update automation
    DELETE /automations/{id}     – delete automation
    POST   /automations/{id}/run – manual trigger
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_automation_service
from core.exceptions import NotFoundError
from models.user import User
from schemas.automation import AutomationCreate, AutomationUpdate, AutomationInDB
from services.automation_service import AutomationService

router = APIRouter(prefix="/automations", tags=["automations"])


@router.get("", response_model=List[AutomationInDB])
async def list_automations(
    user: User = Depends(get_current_user),
    svc: AutomationService = Depends(get_automation_service),
):
    """List all automations for the authenticated user."""
    return await concurrency_manager.run_in_thread(svc.list_automations, user.id)


@router.get("/{automation_id}", response_model=AutomationInDB)
async def get_automation(
    automation_id: UUID,
    user: User = Depends(get_current_user),
    svc: AutomationService = Depends(get_automation_service),
):
    """Get a single automation by ID."""
    result = await concurrency_manager.run_in_thread(svc.get_automation, user.id, automation_id)
    if not result:
        raise NotFoundError("Automation not found")
    return result


@router.post("", response_model=AutomationInDB, status_code=status.HTTP_201_CREATED)
async def create_automation(
    body: AutomationCreate,
    user: User = Depends(get_current_user),
    svc: AutomationService = Depends(get_automation_service),
):
    """Create a new scheduled automation."""
    return await concurrency_manager.run_in_thread(svc.create_automation, user.id, body)


@router.patch("/{automation_id}", response_model=AutomationInDB)
async def update_automation(
    automation_id: UUID,
    body: AutomationUpdate,
    user: User = Depends(get_current_user),
    svc: AutomationService = Depends(get_automation_service),
):
    """Update an automation."""
    result = await concurrency_manager.run_in_thread(
        svc.update_automation, user.id, automation_id, body,
    )
    if not result:
        raise NotFoundError("Automation not found")
    return result


@router.delete("/{automation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation(
    automation_id: UUID,
    user: User = Depends(get_current_user),
    svc: AutomationService = Depends(get_automation_service),
):
    """Delete an automation."""
    ok = await concurrency_manager.run_in_thread(svc.delete_automation, user.id, automation_id)
    if not ok:
        raise NotFoundError("Automation not found")


@router.post("/{automation_id}/run")
async def run_automation(
    automation_id: UUID,
    user: User = Depends(get_current_user),
    svc: AutomationService = Depends(get_automation_service),
):
    """Manually trigger an automation immediately."""
    result = await concurrency_manager.run_in_thread(svc.run_now, user.id, automation_id)
    if result is None:
        raise NotFoundError("Automation not found")
    return {"success": True, "answer": (result.get("answer", ""))[:2000]}
