"""Onboarding endpoint: persist user setup preferences."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_settings_service
from core.exceptions import ValidationError
from models.user import User
from services.settings_service import SettingsService

router = APIRouter(prefix="/onboarding", tags=["onboarding"])



class OnboardingRequest(BaseModel):
    user_name: Optional[str] = Field(None, max_length=255, description="Director's name")
    specialization: Optional[str] = Field(None, max_length=50)
    data_sources: List[str] = Field(default_factory=list)
    agent_name: Optional[str] = Field(None, max_length=255)
    tone: Optional[str] = Field(None, max_length=50)
    directives: Optional[str] = Field(None, max_length=2000)


class OnboardingResponse(BaseModel):
    success: bool = True
    onboarding_completed: bool = True



@router.post("", response_model=OnboardingResponse)
async def save_onboarding(
    body: OnboardingRequest,
    user: User = Depends(get_current_user),
    svc: SettingsService = Depends(get_settings_service),
):
    """Persist onboarding data into the user's profile.

    Creates the UserProfile row if it doesn't exist yet, then marks
    onboarding as complete.
    """
    def _query():
        success, error = svc.complete_onboarding(
            user_id=user.id,
            full_name=body.user_name,
            specialization=body.specialization,
            data_sources=body.data_sources,
            agent_name=body.agent_name,
            tone=body.tone,
            directives=body.directives,
        )
        if not success:
            raise ValidationError(error or "Onboarding failed")
        return OnboardingResponse()

    return await concurrency_manager.run_in_thread(_query)
