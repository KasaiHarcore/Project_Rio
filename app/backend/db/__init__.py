"""Database Package for SQLAlchemy ORM.

This module provides:
- Session management (get_db, get_session, get_db_context)
- Base class and mixins for models
- Model imports for convenience
- Repository layer for data access

Usage:
    from backend.db import get_db, User, UserRepository
    
    # FastAPI dependency
    @app.get("/users")
    def get_users(db: Session = Depends(get_db)):
        repo = UserRepository(db)
        return repo.get_multi()
"""

from backend.db.base import Base, TimestampMixin
from backend.db.session import (
    get_db,
    get_db_context,
    get_session,
    get_engine,
    get_session_factory,
    init_db,
    drop_db,
)

# Re-export models for convenience
from backend.db.models import (
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
    RunStep,
    RunStepType,
    RunStepStatus,
    RunEvaluation,
    EvaluationVerdict,
)

# Re-export repositories for convenience
from backend.db.repositories import (
    UserRepository,
    UserProfileRepository,
    ThreadRepository,
    MessageRepository,
    RunRepository,
    ToolUsageRepository,
    AuditLogRepository,
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
    "RunStep",
    "RunStepType",
    "RunStepStatus",
    "RunEvaluation",
    "EvaluationVerdict",
    # Repositories
    "UserRepository",
    "UserProfileRepository",
    "ThreadRepository",
    "MessageRepository",
    "RunRepository",
    "ToolUsageRepository",
    "AuditLogRepository",
]
