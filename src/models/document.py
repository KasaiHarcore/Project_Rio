"""Document model for tracking uploaded knowledge base files."""

from typing import Optional
from enum import Enum

import uuid
from sqlalchemy import String, Integer, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from models.base import Base, TimestampMixin


class DocumentStatus(str, Enum):
    """Processing status for uploaded documents."""
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class Document(Base, TimestampMixin):
    """Tracks files uploaded to the knowledge base (Qdrant vector store).

    Attributes:
        id: UUID primary key
        user_id: Uploader
        name: Original filename
        file_type: Extension (pdf, csv, md, …)
        size_bytes: File size in bytes
        chunk_count: Number of chunks indexed in Qdrant
        status: processing | ready | error
        error_message: Error details if status == error
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False)

    file_type: Mapped[str] = mapped_column(String(20), nullable=False)

    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus),
        nullable=False,
        default=DocumentStatus.PROCESSING,
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        String(2000), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("ix_document_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, name={self.name}, status={self.status})>"
