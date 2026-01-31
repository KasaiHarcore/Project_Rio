"""Pydantic Schemas for Request/Response Validation.

This module provides:
- User and UserProfile schemas (create, update, read)
- Thread and Message schemas
- Tool usage tracking schemas
- Audit log schemas
- Chat history buffer schemas
- API response envelopes
- Admin dashboard schemas

Schema Naming Convention:
    - *Base: Shared fields between create/update/read
    - *Create: Fields required for creation
    - *Update: Optional fields for partial updates
    - *InDB: Full model with DB-generated fields (id, timestamps)

Usage:
    from backend.schemas import UserCreate, UserInDB, ChatResponse
"""

# User schemas
from backend.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserInDB,
    UserProfileBase,
    UserProfileUpdate,
    UserProfileInDB,
)

# Thread schemas
from backend.schemas.thread import (
    ThreadBase,
    ThreadCreate,
    ThreadUpdate,
    ThreadInDB,
)

# Message schemas
from backend.schemas.message import (
    MessageBase,
    MessageCreate,
    MessageUpdate,
    MessageInDB,
)

# Tool usage schemas
from backend.schemas.tool_usage import (
    ToolUsageBase,
    ToolUsageCreate,
    ToolUsageUpdate,
    ToolUsageInDB,
)

# Audit log schemas
from backend.schemas.audit_log import (
    AuditLogBase,
    AuditLogCreate,
    AuditLogInDB,
)

# Chat history schemas
from backend.schemas.query import (
    ChatMessageRecord,
    ChatHistoryBuffer,
    ChatHistorySave,
    ChatMessageRecordModel,
    normalize_chat_history,
)

# Response schemas
from backend.schemas.response import (
    ErrorDetail,
    BaseResponse,
    ErrorResponse,
    ChatStats,
    ChatResponse,
)

# Memory schemas
from backend.schemas.memory import MemoryType

# Admin schemas
from backend.schemas.admin import (
    AdminUserView,
    AdminUserList,
    AdminThreadView,
    AdminThreadList,
    AdminMessageView,
    AdminMessageList,
    AdminToolUsageView,
    AdminToolUsageList,
    AdminToolUsageStats,
    AdminAuditLogView,
    AdminAuditLogList,
    AdminSystemStats,
    AdminUserUpdateAction,
    AdminBulkDeleteAction,
)

__all__ = [
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "UserProfileBase",
    "UserProfileUpdate",
    "UserProfileInDB",
    # Thread
    "ThreadBase",
    "ThreadCreate",
    "ThreadUpdate",
    "ThreadInDB",
    # Message
    "MessageBase",
    "MessageCreate",
    "MessageUpdate",
    "MessageInDB",
    # Tool Usage
    "ToolUsageBase",
    "ToolUsageCreate",
    "ToolUsageUpdate",
    "ToolUsageInDB",
    # Audit Log
    "AuditLogBase",
    "AuditLogCreate",
    "AuditLogInDB",
    # Chat History
    "ChatMessageRecord",
    "ChatHistoryBuffer",
    "ChatHistorySave",
    "ChatMessageRecordModel",
    "normalize_chat_history",
    # Response
    "ErrorDetail",
    "BaseResponse",
    "ErrorResponse",
    "ChatStats",
    "ChatResponse",
    # Memory
    "MemoryType",
    # Admin
    "AdminUserView",
    "AdminUserList",
    "AdminThreadView",
    "AdminThreadList",
    "AdminMessageView",
    "AdminMessageList",
    "AdminToolUsageView",
    "AdminToolUsageList",
    "AdminToolUsageStats",
    "AdminAuditLogView",
    "AdminAuditLogList",
    "AdminSystemStats",
    "AdminUserUpdateAction",
    "AdminBulkDeleteAction",
]
