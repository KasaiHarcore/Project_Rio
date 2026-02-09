"""SQLAlchemy ORM Models for Application Entities.

Model Hierarchy:
    User
    ├── UserProfile (1:1)
    ├── Thread (1:N)
    │   └── Message (1:N)
    └── AuditLog (1:N)
"""

from infrastructure.dto.models.user import User, UserRole
from infrastructure.dto.models.thread import Thread, ThreadStatus
from infrastructure.dto.models.message import Message, MessageRole
from infrastructure.dto.models.user_profile import UserProfile
from infrastructure.dto.models.audit_log import AuditLog

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
