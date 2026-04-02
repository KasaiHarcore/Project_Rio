"""Pydantic Schemas for AudioOverview model."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AudioGenerateRequest(BaseModel):
    source_ids: List[str] = Field(..., min_length=1, max_length=10)
    source_type: str = Field("notes", description="notes | documents | flashcards")
    format: str = Field("summary", description="summary | dialogue | lecture")
    title: Optional[str] = Field(None, max_length=500)


class AudioOverviewInDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    source_ids: List[str]
    source_type: str
    transcript: Optional[str] = None
    audio_path: Optional[str] = None
    duration_seconds: Optional[int] = None
    format: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
