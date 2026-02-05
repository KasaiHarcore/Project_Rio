"""ToolUsage model for logging tool calls."""

from typing import Optional
from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from enum import Enum
from backend.infrastructure.dto.base import Base


class ToolStatus(str, Enum):
    """Tool execution status enumeration."""
    SUCCESS = "success"
    FAILED = "failed"


class ToolUsage(Base):
    """ToolUsage model for logging tool calls and their results.
    
    Tracks usage of tools like Tavily, Qdrant queries, etc. for routing logic.
    
    Attributes:
        id: UUID primary key
        message_id: Foreign key to Message
        tool_name: Name of the tool (e.g., 'web_scraping', 'qdrant_search')
        status: Execution status (success or failed)
        error_message: Error message if failed
        created_at: Timestamp when tool was called
        message: Relationship to Message model
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    tool_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    status: Mapped[ToolStatus] = mapped_column(
        SQLEnum(ToolStatus),
        nullable=False,
        index=True
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    # Relationships
    message: Mapped["Message"] = relationship(
        "Message",
        back_populates="tool_usages"
    )
    
    def __repr__(self) -> str:
        return f"<ToolUsage(id={self.id}, tool={self.tool_name}, status={self.status})>"
