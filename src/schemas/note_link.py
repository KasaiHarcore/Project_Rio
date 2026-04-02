"""Pydantic Schemas for NoteLink Model.

Schemas:
    - NoteLinkMediaMeta: Optional metadata (timestamp, page, thumbnail)
    - NoteLinkCreate: New link payload
    - NoteLinkUpdate: Partial update payload
    - NoteLinkInDB: Full link with DB fields
    - NoteGraphNode / NoteGraphEdge / NoteGraphResponse: Graph visualization
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.note_link import NoteLinkTargetType


class NoteLinkMediaMeta(BaseModel):
    """Optional metadata for media/URL links."""
    timestamp_start: Optional[int] = Field(None, description="Start time in seconds")
    timestamp_end: Optional[int] = Field(None, description="End time in seconds")
    page_number: Optional[int] = Field(None, description="Slide/PDF page number")
    thumbnail_url: Optional[str] = Field(None, max_length=2000, description="Thumbnail URL")
    mime_type: Optional[str] = Field(None, max_length=100, description="MIME type")
    description: Optional[str] = Field(None, max_length=1000, description="Description")


class NoteLinkCreate(BaseModel):
    """Schema for creating a note link manually."""
    note_id: UUID = Field(..., description="Source note UUID")
    label: str = Field(..., max_length=500, description="Display text")
    target_type: NoteLinkTargetType = Field(..., description="Target resource type")
    target_note_id: Optional[UUID] = Field(None, description="Target note UUID")
    target_document_id: Optional[UUID] = Field(None, description="Target document UUID")
    target_artifact_id: Optional[UUID] = Field(None, description="Target artifact UUID")
    target_url: Optional[str] = Field(None, max_length=2000, description="Target URL")
    media_meta: Optional[NoteLinkMediaMeta] = Field(None, description="Media metadata")
    position: Optional[int] = Field(None, ge=0, description="Char offset in note content")

    @model_validator(mode="after")
    def validate_target(self) -> "NoteLinkCreate":
        """Ensure correct target field is set for the given target_type."""
        tt = self.target_type
        if tt == NoteLinkTargetType.NOTE and not self.target_note_id:
            raise ValueError("target_note_id is required when target_type is 'note'")
        if tt == NoteLinkTargetType.DOCUMENT and not self.target_document_id:
            raise ValueError("target_document_id is required when target_type is 'document'")
        if tt == NoteLinkTargetType.ARTIFACT and not self.target_artifact_id:
            raise ValueError("target_artifact_id is required when target_type is 'artifact'")
        if tt in (NoteLinkTargetType.MEDIA, NoteLinkTargetType.URL) and not self.target_url:
            raise ValueError("target_url is required when target_type is 'media' or 'url'")
        return self


class NoteLinkBulkCreate(BaseModel):
    """Schema for bulk creating note links."""
    links: List[NoteLinkCreate] = Field(..., max_length=50, description="Links to create")


class NoteLinkUpdate(BaseModel):
    """Schema for partial note link update.

    target_type and target IDs are immutable — only label, URL, meta, position can change.
    """
    label: Optional[str] = Field(None, max_length=500)
    target_url: Optional[str] = Field(None, max_length=2000)
    media_meta: Optional[NoteLinkMediaMeta] = None
    position: Optional[int] = Field(None, ge=0)


class NoteLinkInDB(BaseModel):
    """Full note link record returned from the database."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    note_id: UUID
    label: str
    target_type: NoteLinkTargetType
    target_note_id: Optional[UUID] = None
    target_document_id: Optional[UUID] = None
    target_artifact_id: Optional[UUID] = None
    target_url: Optional[str] = None
    media_meta: Optional[Dict] = None
    position: Optional[int] = None
    created_at: datetime
    updated_at: datetime



class NoteGraphNode(BaseModel):
    """A node in the note graph."""
    id: UUID
    type: str = Field(..., description="node type: note | document | artifact | url")
    label: str
    metadata: Optional[Dict] = None


class NoteGraphEdge(BaseModel):
    """An edge in the note graph."""
    source_id: UUID
    target_id: UUID
    label: str
    target_type: NoteLinkTargetType


class NoteGraphStats(BaseModel):
    """Statistics about the note graph."""
    total_nodes: int = 0
    total_edges: int = 0
    total_notes: int = 0
    total_links: int = 0
    returned_nodes: int = 0
    returned_edges: int = 0
    truncated: bool = False


class NoteGraphResponse(BaseModel):
    """Full graph response for visualization."""
    nodes: List[NoteGraphNode] = Field(default_factory=list)
    edges: List[NoteGraphEdge] = Field(default_factory=list)
    stats: NoteGraphStats = Field(default_factory=NoteGraphStats)
