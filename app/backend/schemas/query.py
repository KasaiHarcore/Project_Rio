"""Chat History Typing and Validation Models.

This module provides:
    - ChatMessageRecord: TypedDict for chat messages
    - ChatHistoryBuffer: TypedDict for LLM context
    - ChatHistorySave: TypedDict for saving messages
    - ChatMessageRecordModel: Pydantic validation model
    - normalize_chat_history: Validation utility function

Usage:
    history = normalize_chat_history(
        history=raw_messages,
        max_items=50,
    )
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal, TypedDict, Iterable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError


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


class ChatMessageRecordModel(BaseModel):
	"""Pydantic validation model for chat message records.

	Notes:
	- Extra keys are ignored to keep compatibility with evolving metadata.
	- `content` is required and must be non-empty after stripping.
	"""

	model_config = ConfigDict(extra="ignore")

	role: Literal["user", "assistant", "tool"] = Field(..., description="Message role")
	content: str = Field(..., min_length=1, description="Message content")
	metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")
	created_at: Optional[datetime] = Field(default=None, description="Optional timestamp")

	@staticmethod
	def _clean_content(value: str) -> str:
		return "\n".join([line.rstrip() for line in (value or "").strip().splitlines()]).strip()

	def model_post_init(self, __context: Any) -> None:  # type: ignore[override]
		self.content = self._clean_content(self.content)
		if not self.content:
			raise ValueError("content must be non-empty")


def normalize_chat_history(
	*,
	history: Optional[Iterable[Dict[str, Any]]],
	max_items: int = 50,
) -> List[ChatMessageRecord]:
	"""Validate and normalize a chat history list.

	Behavior:
	- Drops items missing required fields or with empty content.
	- Ignores unknown fields.
	- Returns at most the last `max_items` items (when max_items > 0).

	This is intended to be used at boundaries before passing history into LLMs/LangGraph.
	"""
	if not history:
		return []

	if max_items < 0:
		raise ValueError("max_items must be >= 0")

	validated: List[ChatMessageRecord] = []
	for raw in history:
		if not raw:
			continue
		try:
			item = ChatMessageRecordModel.model_validate(raw)
			validated.append(item.model_dump(exclude_none=True))
		except (ValidationError, ValueError):
			continue

	if max_items == 0:
		return []
	if max_items and len(validated) > max_items:
		return validated[-max_items:]
	return validated
