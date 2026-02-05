"""SQLAlchemy ORM Models for Application Entities.

Model Hierarchy:
    User
    ├── UserProfile (1:1)
    ├── Thread (1:N)
    │   ├── Message (1:N)
    │   │   └── ToolUsage (1:N)
    │   ├── Run (1:N)
    │   └── ThreadSummary (1:1)
    └── AuditLog (1:N)

Standalone:
    - AgentMemory (user memories for personalization)
"""

from backend.infrastructure.dto.models.user import User, UserRole
from backend.infrastructure.dto.models.thread import Thread, ThreadStatus
from backend.infrastructure.dto.models.message import Message, MessageRole
from backend.infrastructure.dto.models.run import Run, RunStatus
from backend.infrastructure.dto.models.user_profile import UserProfile
from backend.infrastructure.dto.models.tool_usage import ToolUsage, ToolStatus
from backend.infrastructure.dto.models.audit_log import AuditLog
from backend.infrastructure.dto.models.agent_memory import AgentMemory, MemoryType
from backend.infrastructure.dto.models.thread_summary import ThreadSummary

__all__ = [
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
]
