"""AuditLog model for tracking user actions."""

from typing import Optional, Dict, Any
from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from backend.db.base import Base


class AuditLog(Base):
    """
    AuditLog model for tracking user actions and system events.
    
    Attributes:
        id: UUID primary key
        user_id: Foreign key to User (nullable for system events)
        action: Action performed (e.g., 'create_message', 'update_thread')
        details: JSONB field for additional context
        created_at: Timestamp when action was logged
        user: Relationship to User model
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    action: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True
    )
    
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="audit_logs"
    )

    __table_args__ = (
        Index("ix_audit_log_user_created", "user_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"
