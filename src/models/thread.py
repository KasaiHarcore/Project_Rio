"""Thread model for LangGraph configuration and chat sessions."""

from typing import List, Optional
from sqlalchemy import String, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from enum import Enum
from models.base import Base, TimestampMixin


class ThreadStatus(str, Enum):
    """Thread status enumeration."""
    ACTIVE = "active"
    ARCHIVED = "archived"


class Thread(Base, TimestampMixin):
    """Thread model for managing LangGraph chat sessions.
    
    Supports multi-thread per user for different conversations.
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User
        title: Optional thread title
        status: Thread status (active or archived)
        created_at: Timestamp when thread was created
        updated_at: Timestamp when thread was last updated
        user: Relationship to User model
        messages: Relationship to Message model
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    title: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    
    status: Mapped[ThreadStatus] = mapped_column(
        SQLEnum(ThreadStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=ThreadStatus.ACTIVE,
        index=True
    )
    
    user: Mapped["User"] = relationship(
        "User",
        back_populates="threads"
    )
    
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )

    __table_args__ = (
        Index("ix_thread_user_updated", "user_id", "updated_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Thread(id={self.id}, user_id={self.user_id}, status={self.status})>"
