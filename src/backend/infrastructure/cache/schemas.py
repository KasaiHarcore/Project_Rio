"""Pydantic schemas for Redis cache / short-term memory payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Role = Literal["user", "assistant", "tool", "system"]


class HotMessage(BaseModel):
	role: Role
	content: str
	ts: datetime = Field(default_factory=datetime.utcnow)


class HotConversationWindow(BaseModel):
	thread_id: str
	messages: List[HotMessage] = Field(default_factory=list)


class WarmConversationSummary(BaseModel):
	thread_id: str
	summary: str
	updated_at: datetime = Field(default_factory=datetime.utcnow)


class SessionState(BaseModel):
	session_id: str
	state: Dict[str, Any] = Field(default_factory=dict)
	updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserShortTermMemory(BaseModel):
	user_id: str
	memory: Dict[str, Any] = Field(default_factory=dict)
	updated_at: datetime = Field(default_factory=datetime.utcnow)


class ToolCacheKey(BaseModel):
	name: str
	params: Dict[str, Any] = Field(default_factory=dict)


class CachedWebResult(BaseModel):
	query: str
	params: Dict[str, Any] = Field(default_factory=dict)
	result: Dict[str, Any]
	cached_at: datetime = Field(default_factory=datetime.utcnow)


class CachedRetrievalResult(BaseModel):
	query: str
	k: int = 10
	result_text: str
	cached_at: datetime = Field(default_factory=datetime.utcnow)
