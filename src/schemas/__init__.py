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

from schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserInDB,
    UserProfileBase,
    UserProfileUpdate,
    UserProfileInDB,
)

from schemas.thread import (
    ThreadBase,
    ThreadCreate,
    ThreadUpdate,
    ThreadInDB,
)

from schemas.message import (
    MessageBase,
    MessageCreate,
    MessageUpdate,
    MessageInDB,
)

from schemas.audit_log import (
    AuditLogBase,
    AuditLogCreate,
    AuditLogInDB,
)

from schemas.query import (
    ChatMessageRecord,
    ChatHistoryBuffer,
    ChatHistorySave,
    ChatMessageRecordModel,
    normalize_chat_history,
)

from schemas.response import (
    ErrorDetail,
    BaseResponse,
    ErrorResponse,
    ChatStats,
    ChatResponse,
)

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

from schemas.mission import (
    MissionBase,
    MissionCreate,
    MissionUpdate,
    MissionInDB,
    MissionStepSchema,
)

from schemas.note import (
    NoteCreate,
    NoteUpdate,
    NoteInDB,
    NoteTodoSchema,
)

from schemas.artifact import (
    ArtifactCreate,
    ArtifactUpdate,
    ArtifactInDB,
)

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
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "UserProfileBase",
    "UserProfileUpdate",
    "UserProfileInDB",
    "ThreadBase",
    "ThreadCreate",
    "ThreadUpdate",
    "ThreadInDB",
    "MessageBase",
    "MessageCreate",
    "MessageUpdate",
    "MessageInDB",
    "AuditLogBase",
    "AuditLogCreate",
    "AuditLogInDB",
    "ChatMessageRecord",
    "ChatHistoryBuffer",
    "ChatHistorySave",
    "ChatMessageRecordModel",
    "normalize_chat_history",
    "ErrorDetail",
    "BaseResponse",
    "ErrorResponse",
    "ChatStats",
    "ChatResponse",
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
    "MissionBase",
    "MissionCreate",
    "MissionUpdate",
    "MissionInDB",
    "MissionStepSchema",
    "NoteCreate",
    "NoteUpdate",
    "NoteInDB",
    "NoteTodoSchema",
    "EmotionalStateResponse",
    "MoodTransition",
    "RelationshipEventResponse",
    "RelationshipHistoryResponse",
    "HeadpatRequest",
    "HeadpatResponse",
    "EmotionalUpdateEvent",
    "ArtifactCreate",
    "ArtifactUpdate",
    "ArtifactInDB",
]
