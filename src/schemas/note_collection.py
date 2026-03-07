"""Pydantic Schemas for NoteCollection Model.

Schemas:
    - CollectionCreate: New collection payload
    - CollectionUpdate: Partial update payload
    - CollectionInDB: Full collection with DB fields + note count
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class CollectionCreate(BaseModel):
    """Schema for creating a new collection."""
    name: str = Field(..., min_length=1, max_length=200, description="Collection name")


class CollectionUpdate(BaseModel):
    """Schema for partial collection update."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)


class CollectionInDB(BaseModel):
    """Full collection record returned from the database."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    note_count: int = Field(0, description="Number of notes in this collection")
    created_at: datetime
    updated_at: datetime
