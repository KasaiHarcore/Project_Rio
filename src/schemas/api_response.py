"""Generic API response schemas with full type hints.

Provides standardized response envelopes:
- ApiResponse[T]       — single item response
- PaginatedResponse[T] — paginated list response
- ErrorDetail          — structured error body
- ResponseMeta         — request metadata
- PaginationMeta       — pagination info
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

class ErrorDetail(BaseModel):
    """Structured error detail returned in API error responses."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional debug context")
    request_id: Optional[str] = Field(None, description="Request correlation ID")

class ResponseMeta(BaseModel):
    """Metadata attached to every API response."""

    request_id: str = Field(..., description="Unique request correlation ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Server-side UTC timestamp",
    )
    duration_ms: Optional[float] = Field(None, description="Request processing time (ms)")

class PaginationMeta(BaseModel):
    """Pagination details for list endpoints."""

    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    per_page: int = Field(..., ge=1, le=200, description="Items per page")
    total: int = Field(..., ge=0, description="Total item count")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether a next page exists")
    has_prev: bool = Field(..., description="Whether a previous page exists")

    @classmethod
    def compute(cls, *, page: int, per_page: int, total: int) -> "PaginationMeta":
        """Create from raw pagination parameters."""
        total_pages = max(1, (total + per_page - 1) // per_page)
        return cls(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )

class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper.

    All successful responses return ``success=True`` with data in ``data``.
    Error responses return ``success=False`` with details in ``error``.

    Examples::

        # Success
        ApiResponse[UserInDB](data=user_data)

        # Error (built by exception handlers)
        ApiResponse(success=False, error=ErrorDetail(code="NOT_FOUND", message="..."))
    """

    success: bool = Field(True, description="Whether the request succeeded")
    data: Optional[T] = Field(None, description="Response payload")
    error: Optional[ErrorDetail] = Field(None, description="Error details (on failure)")
    meta: Optional[ResponseMeta] = Field(None, description="Request metadata")

class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response for list endpoints.

    Example::

        PaginatedResponse[MissionInDB](
            data=missions,
            pagination=PaginationMeta.compute(page=1, per_page=20, total=42),
        )
    """

    success: bool = Field(True, description="Whether the request succeeded")
    data: List[T] = Field(default_factory=list, description="Page items")
    pagination: PaginationMeta = Field(..., description="Pagination details")
    error: Optional[ErrorDetail] = Field(None, description="Error details (on failure)")
    meta: Optional[ResponseMeta] = Field(None, description="Request metadata")