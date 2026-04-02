"""Pydantic Schemas for Artifact Model.

Schemas:
    - ArtifactCreate: New artifact payload
    - ArtifactUpdate: Partial update payload
    - ArtifactInDB: Full artifact with DB fields
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class ArtifactCreate(BaseModel):
    """Schema for creating a new artifact."""
    name: str = Field(..., min_length=1, max_length=255, description="File name")
    artifact_type: str = Field("code", description="Type: code | document | data | image")
    language: Optional[str] = Field(None, max_length=50, description="Language or format")
    content: str = Field(..., min_length=1, description="Full file content")
    thread_id: Optional[str] = Field(None, description="Linked thread UUID")
    parent_id: Optional[str] = Field(None, description="Previous version artifact UUID")


class ArtifactUpdate(BaseModel):
    """Schema for partial artifact update."""
    name: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    language: Optional[str] = Field(None, max_length=50)
    artifact_type: Optional[str] = None


class ArtifactInDB(BaseModel):
    """Full artifact record returned from the database."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    thread_id: Optional[UUID] = None
    name: str
    artifact_type: str
    language: Optional[str] = None
    content: str
    version: int
    parent_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
