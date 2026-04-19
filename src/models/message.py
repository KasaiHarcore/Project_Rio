"""Message model for chat history."""

from typing import Any, Dict, List, Optional
from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Index

import uuid
from datetime import datetime
from enum import Enum
from models.base import Base


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(Base):
    """
    Message model for storing chat queries, responses, and tool interactions.
    
    Attributes:
        id: UUID primary key
        thread_id: Foreign key to Thread
        content: Message content (query, response, or tool output)
        role: Message role (user, assistant, or tool)
        run_id: Workflow run ID for linking to LangGraph state
        created_at: Timestamp when message was created
        thread: Relationship to Thread model
        tool_usages: Relationship to ToolUsage model
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("thread.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    run_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    character_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )

    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("message.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        default=None,
    )

    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        index=True
    )

    # Discriminator for role='tool' rows so the tree-view can pick the
    # right worker icon / label without parsing content. Null for
    # user/assistant messages. Indexed for cheap aggregate queries.
    tool_name: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        index=True
    )
    
    thread: Mapped["Thread"] = relationship(
        "Thread",
        back_populates="messages"
    )

    parent: Mapped[Optional["Message"]] = relationship(
        "Message",
        remote_side="Message.id",
        foreign_keys=[parent_id],
        back_populates="children",
    )

    children: Mapped[List["Message"]] = relationship(
        "Message",
        foreign_keys="Message.parent_id",
        back_populates="parent",
        order_by="Message.created_at",
    )

    __table_args__ = (
        Index("ix_message_thread_created", "thread_id", "created_at"),
        Index("ix_message_parent_id", "parent_id"),
    )
    
    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role={self.role}, content='{content_preview}')>"
