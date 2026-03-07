"""Pydantic schemas for the Document (knowledge-base) model."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict
from models.document import DocumentStatus


class DocumentInDB(BaseModel):
    """Full document record returned from the database."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    file_type: str
    size_bytes: int
    chunk_count: int
    status: DocumentStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentResponse(BaseModel):
    """API-facing document representation."""

    id: str
    name: str
    file_type: str
    size_bytes: int
    chunk_count: int
    status: str
    error_message: Optional[str] = None
    uploaded_at: str  # ISO timestamp


class DocumentListResponse(BaseModel):
    success: bool = True
    documents: list[DocumentResponse]


class DocumentUploadResponse(BaseModel):
    success: bool = True
    document: DocumentResponse
    message: str = Field(default="", description="Processing result summary")
