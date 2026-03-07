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
    from schemas import UserCreate, UserInDB, ChatResponse
"""

# User schemas
from schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserInDB,
    UserProfileBase,
    UserProfileUpdate,
    UserProfileInDB,
)

# Thread schemas
from schemas.thread import (
    ThreadBase,
    ThreadCreate,
    ThreadUpdate,
    ThreadInDB,
)

# Message schemas
from schemas.message import (
    MessageBase,
    MessageCreate,
    MessageUpdate,
    MessageInDB,
)

# Audit log schemas
from schemas.audit_log import (
    AuditLogBase,
    AuditLogCreate,
    AuditLogInDB,
)

# Chat history schemas
from schemas.query import (
    ChatMessageRecord,
    ChatHistoryBuffer,
    ChatHistorySave,
    ChatMessageRecordModel,
    normalize_chat_history,
)

# Response schemas
from schemas.response import (
    ErrorDetail,
    BaseResponse,
    ErrorResponse,
    ChatStats,
    ChatResponse,
)

# Admin schemas
from schemas.admin import (
    AdminUserView,
    AdminUserList,
    AdminThreadView,
    AdminThreadList,
    AdminMessageView,
    AdminMessageList,
    AdminToolUsageStats,
    AdminAuditLogView,
    AdminAuditLogList,
    AdminSystemStats,
    AdminUserUpdateAction,
    AdminBulkDeleteAction,
)

# Mission schemas
from schemas.mission import (
    MissionBase,
    MissionCreate,
    MissionUpdate,
    MissionInDB,
    MissionStepSchema,
)

# Note schemas
from schemas.note import (
    NoteCreate,
    NoteUpdate,
    NoteInDB,
    NoteTodoSchema,
)

# Artifact schemas
from schemas.artifact import (
    ArtifactCreate,
    ArtifactUpdate,
    ArtifactInDB,
)

# Emotional state schemas
from schemas.emotional_state import (
    EmotionalStateResponse,
    MoodTransition,
    RelationshipEventResponse,
    RelationshipHistoryResponse,
    HeadpatRequest,
    HeadpatResponse,
    EmotionalUpdateEvent,
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
    # Admin
    "AdminUserView",
    "AdminUserList",
    "AdminThreadView",
    "AdminThreadList",
    "AdminMessageView",
    "AdminMessageList",
    "AdminToolUsageStats",
    "AdminAuditLogView",
    "AdminAuditLogList",
    "AdminSystemStats",
    "AdminUserUpdateAction",
    "AdminBulkDeleteAction",
    # Mission
    "MissionBase",
    "MissionCreate",
    "MissionUpdate",
    "MissionInDB",
    "MissionStepSchema",
    # Note
    "NoteCreate",
    "NoteUpdate",
    "NoteInDB",
    "NoteTodoSchema",
    # Emotional State
    "EmotionalStateResponse",
    "MoodTransition",
    "RelationshipEventResponse",
    "RelationshipHistoryResponse",
    "HeadpatRequest",
    "HeadpatResponse",
    "EmotionalUpdateEvent",
    # Artifact
    "ArtifactCreate",
    "ArtifactUpdate",
    "ArtifactInDB",
]
