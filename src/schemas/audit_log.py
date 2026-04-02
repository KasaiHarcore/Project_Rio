"""Pydantic Schemas for AuditLog Model.

Schemas:
    - AuditLogBase: Common audit log fields
    - AuditLogCreate: New audit log payload
    - AuditLogInDB: Full audit log with DB fields
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class AuditLogBase(BaseModel):
    """Base audit log schema."""
    
    action: str = Field(..., max_length=255, description="Action performed")


class AuditLogCreate(AuditLogBase):
    """Schema for creating a new audit log."""
    
    user_id: Optional[UUID] = Field(None, description="User UUID (nullable for system events)")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class AuditLogInDB(AuditLogBase):
    """Schema for audit log stored in database."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(..., description="AuditLog UUID")
    user_id: Optional[UUID] = Field(None, description="User UUID")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    created_at: datetime = Field(..., description="Creation timestamp")
