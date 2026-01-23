"""Pydantic schemas for ToolUsage model."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from backend.db.models.tool_usage import ToolStatus


class ToolUsageBase(BaseModel):
    """Base tool usage schema."""
    
    tool_name: str = Field(..., max_length=255, description="Tool name")
    status: ToolStatus = Field(..., description="Execution status")


class ToolUsageCreate(ToolUsageBase):
    """Schema for creating a new tool usage record."""

    error_message: Optional[str] = Field(None, description="Error message if failed")


class ToolUsageUpdate(BaseModel):
    """Schema for updating tool usage information."""

    status: Optional[ToolStatus] = Field(None, description="Execution status")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class ToolUsageInDB(ToolUsageBase):
    """Schema for tool usage stored in database."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="ToolUsage UUID")
    message_id: UUID = Field(..., description="Message UUID")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Creation timestamp")
