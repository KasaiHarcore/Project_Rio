"""Onboarding endpoint: persist user setup preferences."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_db
from models.user import User
from models.user_profile import UserProfile

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ── Request / Response schemas ──────────────────────────────────────────────

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


# ── Endpoint ────────────────────────────────────────────────────────────────

@router.post("", response_model=OnboardingResponse)
async def save_onboarding(
    body: OnboardingRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist onboarding data into the user's profile.

    Creates the UserProfile row if it doesn't exist yet, then marks
    onboarding as complete.
    """
    def _query():
        profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()

        if not profile:
            profile = UserProfile(user_id=user.id)
            db.add(profile)

        # Map form fields → profile columns
        if body.user_name:
            profile.full_name = body.user_name
        if body.specialization:
            profile.specialization = body.specialization
        if body.agent_name:
            profile.agent_name = body.agent_name
        if body.tone:
            profile.tone = body.tone
        if body.directives is not None:
            profile.directives = body.directives
        if body.data_sources is not None:
            profile.data_sources = body.data_sources

        profile.onboarding_completed = True

        db.commit()
        db.refresh(profile)

        return OnboardingResponse()

    return await concurrency_manager.run_in_thread(_query)
