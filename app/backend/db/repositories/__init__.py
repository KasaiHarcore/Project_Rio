"""Repository Layer for Database CRUD and Queries.

Repositories encapsulate database access logic, providing:
- Clean separation between business logic and data access
- Consistent error handling with custom exceptions
- Typed methods with proper documentation

Usage:
    from backend.db import get_db, UserRepository
    
    def get_user_service(db: Session = Depends(get_db)):
        repo = UserRepository(db)
        user = repo.get_by_email("user@example.com")
        return user

Exception Handling:
    - DatabaseError: General database failures
    - NotFoundError: Resource not found
    - DuplicateError: Unique constraint violation
"""

from backend.db.repositories.user_repo import UserRepository
from backend.db.repositories.user_profile_repo import UserProfileRepository
from backend.db.repositories.thread_repo import ThreadRepository
from backend.db.repositories.message_repo import MessageRepository
from backend.db.repositories.run_repo import RunRepository
from backend.db.repositories.tool_usage_repo import ToolUsageRepository
from backend.db.repositories.audit_log_repo import AuditLogRepository

__all__ = [
    "UserRepository",
    "UserProfileRepository",
    "ThreadRepository",
    "MessageRepository",
    "RunRepository",
    "ToolUsageRepository",
    "AuditLogRepository",
]
