"""Admin-only Pydantic schemas for dashboard and management.

SECURITY WARNING: These schemas MUST only be used in admin-protected endpoints.
Requires role-based access control and audit logging for all operations.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from backend.db.models.user import UserRole
from backend.db.models.thread import ThreadStatus
from backend.db.models.message import MessageRole
from backend.db.models.tool_usage import ToolStatus

class AdminUserView(BaseModel):
    """Admin view of user with full details and statistics."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    username: str
    email: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
    
    # Statistics
    thread_count: int = Field(0, description="Total number of threads")
    message_count: int = Field(0, description="Total number of messages")
    active_thread_count: int = Field(0, description="Active threads only")


class AdminUserList(BaseModel):
    """Paginated list of users for admin dashboard."""
    
    users: List[AdminUserView]
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")

class AdminThreadView(BaseModel):
    """Admin view of thread with full details."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    title: Optional[str]
    status: ThreadStatus
    created_at: datetime
    updated_at: datetime
    
    # Statistics
    message_count: int = Field(0, description="Number of messages in thread")
    
    # Related data
    username: Optional[str] = Field(None, description="Owner username")


class AdminThreadList(BaseModel):
    """Paginated list of threads for admin dashboard."""
    
    threads: List[AdminThreadView]
    total: int
    page: int
    page_size: int
    has_next: bool

class AdminMessageView(BaseModel):
    """Admin view of message with full content."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    thread_id: UUID
    content: str
    role: MessageRole
    created_at: datetime
    
    # Statistics
    tool_usage_count: int = Field(0, description="Number of tools used")


class AdminMessageList(BaseModel):
    """Paginated list of messages for admin review."""
    
    messages: List[AdminMessageView]
    total: int
    page: int
    page_size: int
    has_next: bool

class AdminToolUsageView(BaseModel):
    """Admin view of tool usage with details."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    message_id: UUID
    tool_name: str
    status: ToolStatus
    error_message: Optional[str]
    created_at: datetime


class AdminToolUsageList(BaseModel):
    """Paginated list of tool usage for analytics."""
    
    tool_usages: List[AdminToolUsageView]
    total: int
    page: int
    page_size: int
    has_next: bool


class AdminToolUsageStats(BaseModel):
    """Aggregated statistics for tool usage."""
    
    total_calls: int
    success_count: int
    failed_count: int
    by_tool: Dict[str, int] = Field(..., description="Call count per tool name")
    avg_calls_per_day: float

class AdminAuditLogView(BaseModel):
    """Admin view of audit log with full details."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: Optional[UUID]
    action: str
    details: Optional[Dict[str, Any]]
    created_at: datetime
    
    # Related data
    username: Optional[str] = Field(None, description="User who performed action")


class AdminAuditLogList(BaseModel):
    """Paginated audit log for admin review."""
    
    logs: List[AdminAuditLogView]
    total: int
    page: int
    page_size: int
    has_next: bool

class AdminSystemStats(BaseModel):
    """Overall system statistics for admin dashboard."""
    
    total_users: int
    total_threads: int
    total_messages: int
    total_tool_calls: int
    
    active_users_today: int
    active_threads: int
    
    avg_messages_per_thread: float
    avg_threads_per_user: float
    
    most_used_tools: List[Dict[str, Any]] = Field(
        ..., 
        description="Top 5 most used tools with counts"
    )
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# ==================== Admin Action Schemas ====================

class AdminUserUpdateAction(BaseModel):
    """Admin action to update user details."""
    
    role: Optional[UserRole] = None


class AdminBulkDeleteAction(BaseModel):
    """Admin action for bulk deletion."""
    
    ids: List[UUID] = Field(..., min_items=1, max_items=100)
    confirm: bool = Field(..., description="Must be True to proceed")
    reason: str = Field(..., min_length=10, description="Reason for deletion")
