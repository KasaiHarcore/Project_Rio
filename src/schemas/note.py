"""Pydantic Schemas for Note Model.

Schemas:
    - NoteTodoSchema: A single TODO item within a note
    - NoteBlockSchema: A single block within a note (heading, text, bullet, etc.)
    - NoteAudioSchema: Audio metadata for a note
    - NoteCreate: New note payload
    - NoteUpdate: Partial update payload
    - NoteInDB: Full note with DB fields
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from models.note import NoteSource


class NoteTodoSchema(BaseModel):
    """A single checklist item within a note."""
    text: str = Field(..., max_length=200, description="TODO item text")
    done: bool = Field(False, description="Whether the item is completed")


class NoteBlockSchema(BaseModel):
    """A single block in the block-based note editor."""
    id: str = Field(..., max_length=50, description="Block unique ID")
    type: str = Field(..., description="Block type: heading, text, bullet, todo, important, divider")
    content: str = Field("", max_length=2000, description="Block text content")
    checked: Optional[bool] = Field(None, description="For todo blocks: whether checked")


class NoteAudioSchema(BaseModel):
    """Audio metadata stored as JSONB on the note."""
    id: str = Field(..., max_length=50, description="Audio unique ID")
    url: Optional[str] = Field(None, max_length=500, description="Path/URL to audio file")
    duration: Optional[float] = Field(None, ge=0, description="Duration in seconds")
    transcript: Optional[str] = Field(None, max_length=50000, description="Transcribed text")


class NoteCreate(BaseModel):
    """Schema for creating a new note."""
    title: Optional[str] = Field("", max_length=500, description="Note title")
    content: str = Field("", max_length=5000, description="Note text (legacy plain text)")
    todos: List[NoteTodoSchema] = Field(default_factory=list, description="Optional TODO checklist")
    blocks: List[NoteBlockSchema] = Field(default_factory=list, description="Block-based content")
    source: NoteSource = Field(NoteSource.USER, description="Creation source")
    thread_id: Optional[str] = Field(None, description="Linked thread UUID (optional)")
    collection_id: Optional[str] = Field(None, description="Collection UUID (optional)")
    is_important: bool = Field(False, description="Whether note is important")
    audio: Optional[NoteAudioSchema] = Field(None, description="Audio metadata")


class NoteUpdate(BaseModel):
    """Schema for partial note update."""
    title: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, max_length=5000)
    todos: Optional[List[NoteTodoSchema]] = None
    blocks: Optional[List[NoteBlockSchema]] = None
    pinned: Optional[bool] = None
    is_important: Optional[bool] = None
    collection_id: Optional[str] = None
    audio: Optional[NoteAudioSchema] = None


class NoteInDB(BaseModel):
    """Full note record returned from the database."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    thread_id: Optional[UUID] = None
    title: Optional[str] = ""
    content: str
    todos: List[NoteTodoSchema] = Field(default_factory=list)
    blocks: List[NoteBlockSchema] = Field(default_factory=list)
    pinned: bool
    is_important: bool = False
    source: NoteSource
    collection_id: Optional[UUID] = None
    audio: Optional[NoteAudioSchema] = None
    created_at: datetime
    updated_at: datetime
