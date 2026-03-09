"""Settings endpoints for managing user preferences and profile."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_settings_service
from core.exceptions import ValidationError
from services.settings_service import SettingsService
from models.user import User
from schemas.user import UserProfileUpdate, UserProfileInDB
from schemas.user_settings import (
    UserSettingsUpdate,
    UserSettingsInDB,
)


router = APIRouter(prefix="/settings", tags=["settings"])


# ── Request / Response schemas ──────────────────────────────────────────────


class UserInfoUpdate(BaseModel):
    """Schema for updating basic user info (username, email)."""

    username: str | None = Field(None, min_length=3, max_length=255)
    email: str | None = Field(None)


class SettingsResponse(BaseModel):
    """Response with full settings data."""

    success: bool = True
    settings: UserSettingsInDB
    profile: UserProfileInDB | None = None


class UpdateResponse(BaseModel):
    """Generic update response."""

    success: bool = True
    message: str = "Updated successfully"


# ── Endpoints ───────────────────────────────────────────────────────────────


@router.get("", response_model=SettingsResponse)
async def get_settings(
    user: User = Depends(get_current_user),
    svc: SettingsService = Depends(get_settings_service),
):
    """Get current user's settings and profile.

    Creates settings/profile with defaults if they don't exist.
    """
    def _query():
        settings = svc.get_settings(user.id)

        # Get profile (with relationship loaded)
        profile = None
        if user.profile:
            profile = UserProfileInDB.model_validate(user.profile)

        return SettingsResponse(settings=settings, profile=profile)

    return await concurrency_manager.run_in_thread(_query)


@router.put("", response_model=SettingsResponse)
async def update_settings(
    updates: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    svc: SettingsService = Depends(get_settings_service),
):
    """Update user settings.

    Only updates fields that are provided in the request body.
    """
    def _query():
        success, settings_data, error = svc.update_settings(
            user.id, updates
        )

        if not success:
            raise ValidationError(error or "Failed to update settings")

        # Get profile
        profile = None
        if user.profile:
            profile = UserProfileInDB.model_validate(user.profile)

        return SettingsResponse(settings=settings_data, profile=profile)

    return await concurrency_manager.run_in_thread(_query)


@router.put("/profile", response_model=UpdateResponse)
async def update_profile(
    updates: UserProfileUpdate,
    user: User = Depends(get_current_user),
    svc: SettingsService = Depends(get_settings_service),
):
    """Update user profile (bio, study goals, etc.).

    Only updates fields that are provided in the request body.
    """
    def _query():
        success, error = svc.update_profile(user.id, updates)

        if not success:
            raise ValidationError(error or "Failed to update profile")

        return UpdateResponse(message="Profile updated successfully")

    return await concurrency_manager.run_in_thread(_query)


@router.put("/user-info", response_model=UpdateResponse)
async def update_user_info(
    updates: UserInfoUpdate,
    user: User = Depends(get_current_user),
    svc: SettingsService = Depends(get_settings_service),
):
    """Update basic user information (username, email).

    Only updates fields that are provided in the request body.
    """
    def _query():
        success, error = svc.update_user_info(
            user.id,
            username=updates.username,
            email=updates.email,
        )

        if not success:
            raise ValidationError(error or "Failed to update user info")

        return UpdateResponse(message="User info updated successfully")

    return await concurrency_manager.run_in_thread(_query)
