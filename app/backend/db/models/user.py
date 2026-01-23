"""User model for authentication and authorization."""

from typing import List, Optional
from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from enum import Enum
from backend.db.base import Base, TimestampMixin


class UserRole(str, Enum):
    """User role enumeration."""
    USER = "user"
    ADMIN = "admin"


class User(Base, TimestampMixin):
    """User model for storing user information and authentication.
    
    Attributes:
        id: UUID primary key
        username: Unique username for authentication
        email: Unique email address
        hashed_password: Bcrypt hashed password
        role: User role (user or admin)
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        threads: Relationship to Thread model
        profile: Relationship to UserProfile model
        audit_logs: Relationship to AuditLog model
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        index=True
    )
    
    username: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=False,
        index=True
    )
    
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=False,
        index=True
    )
    
    hashed_password: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole), 
        nullable=False, 
        default=UserRole.USER
    )
    
    # Relationships
    threads: Mapped[List["Thread"]] = relationship(
        "Thread",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    profile: Mapped[Optional["UserProfile"]] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
