"""Pydantic schemas for Thread model."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from backend.db.models.thread import ThreadStatus


class ThreadBase(BaseModel):
    """Base thread schema."""
    
    title: Optional[str] = Field(None, max_length=500, description="Thread title")


class ThreadCreate(ThreadBase):
    """Schema for creating a new thread."""
    
    status: ThreadStatus = Field(default=ThreadStatus.ACTIVE, description="Thread status")


class ThreadUpdate(BaseModel):
    """Schema for updating thread information."""
    
    title: Optional[str] = Field(None, max_length=500, description="New thread title")
    status: Optional[ThreadStatus] = Field(None, description="New thread status")


class ThreadInDB(ThreadBase):
    """Schema for thread stored in database."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="Thread UUID")
    user_id: UUID = Field(..., description="Owner user UUID")
    status: ThreadStatus = Field(..., description="Thread status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
