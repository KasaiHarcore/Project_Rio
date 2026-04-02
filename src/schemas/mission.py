"""Pydantic Schemas for Mission Model.

Schemas:
    - MissionBase: Common mission fields
    - MissionCreate: New mission payload
    - MissionUpdate: Partial update payload
    - MissionInDB: Full mission with DB fields
    - MissionStepSchema: A single sub-task step
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from models.mission import MissionStatus, MissionPriority, MissionSource


class MissionStepSchema(BaseModel):
    """A single checklist step within a mission."""
    text: str = Field(..., max_length=300, description="Step description")
    done: bool = Field(False, description="Whether the step is completed")


class MissionBase(BaseModel):
    """Base mission schema — shared fields."""
    title: str = Field(..., min_length=1, max_length=500, description="Mission title")
    description: Optional[str] = Field(None, max_length=10000, description="Longer description")
    priority: MissionPriority = Field(MissionPriority.NORMAL, description="Priority level")
    tags: List[str] = Field(default_factory=list, description="Tag labels")
    steps: List[MissionStepSchema] = Field(default_factory=list, description="Checklist steps")
    # Notion-style scheduling & categorization
    deadline: Optional[datetime] = Field(None, description="Due date/time (ISO 8601)")
    scheduled_start: Optional[datetime] = Field(None, description="Planned start date/time")
    estimated_minutes: Optional[int] = Field(None, ge=1, le=14400, description="Estimated time to complete in minutes")
    meet_url: Optional[str] = Field(None, max_length=500, description="Optional meeting link (Meet, Zoom, etc.)")
    category: Optional[str] = Field(None, max_length=100, description="Category label (like Notion Select)")
    notes: Optional[str] = Field(None, max_length=10000, description="Rich notes / additional context")


class MissionCreate(MissionBase):
    """Schema for creating a new mission."""
    status: MissionStatus = Field(MissionStatus.ACTIVE, description="Initial status")
    source: MissionSource = Field(MissionSource.USER, description="Creation source")
    thread_id: Optional[str] = Field(None, description="Linked thread UUID (optional)")


class MissionUpdate(BaseModel):
    """Schema for partial mission update."""
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=10000)
    status: Optional[MissionStatus] = None
    priority: Optional[MissionPriority] = None
    tags: Optional[List[str]] = None
    steps: Optional[List[MissionStepSchema]] = None
    sort_order: Optional[int] = None
    progress: Optional[int] = Field(None, ge=0, le=100)
    deadline: Optional[datetime] = None
    scheduled_start: Optional[datetime] = None
    estimated_minutes: Optional[int] = Field(None, ge=1, le=14400)
    meet_url: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=10000)


class MissionInDB(MissionBase):
    """Full mission record returned from the database."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    thread_id: Optional[UUID] = None
    status: MissionStatus
    source: MissionSource
    progress: int
    sort_order: int
    created_at: datetime
    updated_at: datetime
