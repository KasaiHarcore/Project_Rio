"""Pydantic Schemas for Message Model.

Schemas:
    - MessageBase: Common message fields
    - MessageCreate: New message payload
    - MessageUpdate: Partial update payload
    - MessageInDB: Full message with DB fields
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from backend.infrastructure.dto.models.message import MessageRole


class MessageBase(BaseModel):
    """Base message schema."""
    
    content: str = Field(..., min_length=1, description="Message content")
    role: MessageRole = Field(..., description="Message role")


class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    
    run_id: Optional[str] = Field(None, description="Workflow run ID")


class MessageUpdate(BaseModel):
    """Schema for updating message information."""
    
    content: Optional[str] = Field(None, min_length=1, description="New message content")
    run_id: Optional[str] = Field(None, description="Workflow run ID")


class MessageInDB(MessageBase):
    """Schema for message stored in database."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="Message UUID")
    thread_id: UUID = Field(..., description="Thread UUID")
    run_id: Optional[str] = Field(None, description="Workflow run ID")
    created_at: datetime = Field(..., description="Creation timestamp")
