"""Pydantic schemas for Redis cache / short-term memory payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from utils.timezone import utc_now


Role = Literal["user", "assistant", "tool", "system"]


class HotMessage(BaseModel):
	role: Role
	content: str
	ts: datetime = Field(default_factory=utc_now)


class WarmConversationSummary(BaseModel):
	thread_id: str
	summary: str
	updated_at: datetime = Field(default_factory=utc_now)


class CachedWebResult(BaseModel):
	query: str
	params: Dict[str, Any] = Field(default_factory=dict)
	result: Dict[str, Any]
	cached_at: datetime = Field(default_factory=utc_now)


class CachedRetrievalResult(BaseModel):
	query: str
	k: int = 10
	result_text: str
	cached_at: datetime = Field(default_factory=utc_now)
