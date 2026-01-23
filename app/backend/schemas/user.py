"""Pydantic schemas for User model."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from backend.db.models.user import UserRole


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
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    profile: Optional[UserProfileInDB] = Field(None, description="User profile")
