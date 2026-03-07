"""Pydantic Schemas for User and UserProfile Models.

Schemas:
    - UserBase: Common user fields
    - UserCreate: Registration payload
    - UserUpdate: Partial update payload
    - UserInDB: Full user with DB fields
    - UserProfileBase: Common profile fields
    - UserProfileUpdate: Profile update payload
    - UserProfileInDB: Full profile with DB fields
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from models.user import UserRole, AuthProvider


class UserBase(BaseModel):
    """Base user schema."""
    
    username: str = Field(..., min_length=3, max_length=255, description="Unique username")
    email: EmailStr = Field(..., description="User email address")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    
    password: str = Field(..., min_length=8, max_length=100, description="User password")
    role: UserRole = Field(default=UserRole.USER, description="User role")


class UserUpdate(BaseModel):
    """Schema for updating user information."""
    
    username: Optional[str] = Field(None, min_length=3, max_length=255, description="New username")
    email: Optional[EmailStr] = Field(None, description="New email address")
    password: Optional[str] = Field(None, min_length=8, max_length=100, description="New password")
    role: Optional[UserRole] = Field(None, description="New role")


class UserProfileBase(BaseModel):
    """Base user profile schema (user-provided fields only)."""

    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")
    address: Optional[str] = Field(None, max_length=500, description="Address")
    company: Optional[str] = Field(None, max_length=255, description="Company")
    job_title: Optional[str] = Field(None, max_length=255, description="Job title")
    locale: Optional[str] = Field(None, max_length=50, description="Locale")
    specialization: Optional[str] = Field(None, max_length=50, description="Agent specialization")
    agent_name: Optional[str] = Field(None, max_length=255, description="Custom agent name")
    tone: Optional[str] = Field(None, max_length=50, description="Agent tone")
    directives: Optional[str] = Field(None, max_length=2000, description="Prime directives")
    data_sources: Optional[List[str]] = Field(None, description="Selected data sources (cloud, repo, local)")
    onboarding_completed: Optional[bool] = Field(None, description="Onboarding completed")
    bio: Optional[str] = Field(None, max_length=1000, description="User bio")
    study_goal: Optional[str] = Field(None, max_length=1000, description="Study goals")


class UserProfileUpdate(UserProfileBase):
    """Schema for updating user profile."""


class UserProfileInDB(UserProfileBase):
    """Schema for user profile stored in database."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Profile UUID")
    user_id: UUID = Field(..., description="User UUID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UserInDB(UserBase):
    """Schema for user stored in database."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="User UUID")
    role: UserRole = Field(..., description="User role")
    auth_provider: AuthProvider = Field(AuthProvider.LOCAL, description="Login type: local, google, github")
    avatar_url: Optional[str] = Field(None, description="Profile picture URL")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    profile: Optional[UserProfileInDB] = Field(None, description="User profile")


class OAuthLoginResponse(BaseModel):
    """Response after successful OAuth2 login/registration."""

    success: bool = True
    user: UserInDB
    tokens: "TokenPairSchema"
    is_new_user: bool = Field(False, description="True if the account was just created")


class TokenPairSchema(BaseModel):
    """Token pair for API responses."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token TTL in seconds")


# Update forward ref
OAuthLoginResponse.model_rebuild()

