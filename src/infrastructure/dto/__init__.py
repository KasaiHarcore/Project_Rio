"""Database Package for SQLAlchemy ORM.

This module provides:
- Session management (get_db, get_session, get_db_context)
- Base class and mixins for models
- Model imports for convenience

Usage:
    from infrastructure.dto import get_db, User, Thread
    
    # FastAPI dependency
    @app.get("/users")
    def get_users(db: Session = Depends(get_db)):
        return db.query(User).all()
"""

from infrastructure.dto.base import Base, TimestampMixin
from infrastructure.dto.session import (
    get_db,
    get_db_context,
    get_session,
    get_engine,
    get_session_factory,
    init_db,
    drop_db,
)

# Re-export models for convenience
from infrastructure.dto.models import (
    User,
    UserRole,
    Thread,
    ThreadStatus,
    Message,
    MessageRole,
    UserProfile,
    AuditLog,
)

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # Session
    "get_db",
    "get_db_context",
    "get_session",
    "get_engine",
    "get_session_factory",
    "init_db",
    "drop_db",
    # Models
    "User",
    "UserRole",
    "Thread",
    "ThreadStatus",
    "Message",
    "MessageRole",
    "UserProfile",
    "AuditLog",
]
