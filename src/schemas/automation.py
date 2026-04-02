"""Pydantic Schemas for Automation model."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AutomationCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: str = Field("", max_length=2000)
    cron_expression: str = Field(..., max_length=100)
    timezone: str = Field("UTC", max_length=50)
    agent_instruction: str = Field(..., max_length=10000)
    agent_mode: str = Field("chat")
    result_delivery: str = Field("notification")
    max_runs: Optional[int] = Field(None, ge=1)


class AutomationUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    agent_instruction: Optional[str] = None
    agent_mode: Optional[str] = None
    result_delivery: Optional[str] = None
    enabled: Optional[bool] = None
    max_runs: Optional[int] = None


class AutomationInDB(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = ""
    cron_expression: str
    timezone: str
    agent_instruction: str
    agent_mode: str
    result_delivery: str
    enabled: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    run_count: int
    max_runs: Optional[int] = None
    last_result: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
