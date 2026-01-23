"""Typing models for chat history."""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal, TypedDict
from uuid import UUID


class ChatMessageRecord(TypedDict, total=False):
	"""Normalized chat message record (markdown preferred)."""

	role: Literal["user", "assistant", "tool"]
	content: str
	metadata: Optional[Dict[str, Any]]
	created_at: Optional[datetime]


class ChatHistoryBuffer(TypedDict, total=False):
	"""Chat memory buffer for LLM context."""

	thread_id: UUID
	messages: List[ChatMessageRecord]


class ChatHistorySave(TypedDict, total=False):
	"""Schema for saving a chat message."""

	thread_id: Optional[UUID]
	role: Literal["user", "assistant", "tool"]
	content: str
	metadata: Optional[Dict[str, Any]]
