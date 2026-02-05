"""Database Package for SQLAlchemy ORM.

This module provides:
- Session management (get_db, get_session, get_db_context)
- Base class and mixins for models
- Model imports for convenience

Usage:
    from backend.infrastructure.dto import get_db, User, Thread
    
    # FastAPI dependency
    @app.get("/users")
    def get_users(db: Session = Depends(get_db)):
        return db.query(User).all()
"""

from backend.infrastructure.dto.base import Base, TimestampMixin
from backend.infrastructure.dto.session import (
    get_db,
    get_db_context,
    get_session,
    get_engine,
    get_session_factory,
    init_db,
    drop_db,
)

# Re-export models for convenience
from backend.infrastructure.dto.models import (
    User,
    UserRole,
    Thread,
    ThreadStatus,
    Message,
    MessageRole,
    Run,
    RunStatus,
    UserProfile,
    ToolUsage,
    ToolStatus,
    AuditLog,
    AgentMemory,
    MemoryType,
    ThreadSummary,
)

# Re-export repositories for convenience
from backend.infrastructure.dto.repositories import (
    RunRepository,
    ToolUsageRepository,
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
    "Run",
    "RunStatus",
    "UserProfile",
    "ToolUsage",
    "ToolStatus",
    "AuditLog",
    "AgentMemory",
    "MemoryType",
    "ThreadSummary",
    # Repositories
    "RunRepository",
    "ToolUsageRepository",
]
