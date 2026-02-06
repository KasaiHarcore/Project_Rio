"""SQLAlchemy ORM Models for Application Entities.

Model Hierarchy:
    User
    ├── UserProfile (1:1)
    ├── Thread (1:N)
    │   └── Message (1:N)
    └── AuditLog (1:N)
"""

from backend.infrastructure.dto.models.user import User, UserRole
from backend.infrastructure.dto.models.thread import Thread, ThreadStatus
from backend.infrastructure.dto.models.message import Message, MessageRole
from backend.infrastructure.dto.models.user_profile import UserProfile
from backend.infrastructure.dto.models.audit_log import AuditLog

__all__ = [
    "User",
    "UserRole",
    "Thread",
    "ThreadStatus",
    "Message",
    "MessageRole",
    "UserProfile",
    "AuditLog",
]
