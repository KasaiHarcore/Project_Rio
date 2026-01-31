"""Shared Response Envelopes and Error Payloads.

This module provides standardized API response formats:
    - BaseResponse: Base with success flag and request_id
    - ErrorResponse: Error with code, message, details
    - ChatResponse: Chat completion with answer and stats

Usage:
    # Success response
    return ChatResponse(
        success=True,
        answer="Hello!",
        stats=ChatStats(total_tokens=100),
    )
    
    # Error response
    return ErrorResponse(
        success=False,
        error=ErrorDetail(
            code="NOT_FOUND",
            message="User not found",
        ),
    )
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
	code: str = Field(..., description="Machine-readable error code")
	message: str = Field(..., description="Human-readable error message")
	details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error context")


class BaseResponse(BaseModel):
	success: bool = Field(..., description="Success flag")
	request_id: Optional[str] = Field(default=None, description="Optional request correlation id")


class ErrorResponse(BaseResponse):
	success: bool = Field(default=False, description="Always false for errors")
	error: ErrorDetail


class ChatStats(BaseModel):
	model: Optional[str] = None
	total_input_tokens: Optional[int] = None
	total_output_tokens: Optional[int] = None
	total_tokens: Optional[int] = None
	total_cost: Optional[float] = None


class ChatResponse(BaseResponse):
	success: bool = Field(default=True)
	answer: str = Field(..., description="Assistant answer")
	stats: Optional[ChatStats] = None
	sources: Optional[List[Dict[str, Any]]] = None
