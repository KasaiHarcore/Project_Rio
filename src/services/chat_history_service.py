"""Chat history service for SQL-backed message persistence.

Handles thread and message persistence to PostgreSQL.
Agent memory is handled by LangGraph's PostgresStore (see memory_store.py).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
import os

from utils.timezone import utc_now, local_now

from infrastructure.database.session import get_db_context
from models.thread import Thread, ThreadStatus
from models.message import Message, MessageRole
from repositories.thread_repository import ThreadRepository
from repositories.message_repository import MessageRepository
from utils.log import log_debug, log_info, log_warning, log_error
from infrastructure.llm import form
from schemas.query import ChatMessageRecord
from infrastructure.cache.service import CacheService


_EXECUTOR = ThreadPoolExecutor(max_workers=2)
WINDOW_ROUNDS = int(os.getenv("CHAT_HISTORY_WINDOW_ROUNDS", "20"))
SUMMARY_PREFIX = "[SUMMARY]"


def _default_thread_title(content: str) -> str:
    cleaned = " ".join((content or "").strip().split())
    return cleaned[:60] if cleaned else f"Chat {local_now().strftime('%Y%m%d_%H%M%S')}"


def _parse_uuid(value: Optional[str | UUID]) -> Optional[UUID]:
    if not value:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except Exception:
        return None


class ChatHistoryService:
    """Service to persist and retrieve chat history.

    SPECIAL: This service uses get_db_context() for background tasks.
    Inside each context manager block, it creates ThreadRepository and
    MessageRepository instances bound to that session.
    """

    def __init__(self) -> None:
        self._cache: Optional[CacheService] = None

    def inject_cache(self, cache: CacheService) -> None:
        """Inject the CacheService instance (called at startup)."""
        self._cache = cache

    def _parse_thread_id(self, thread_id: Optional[str]) -> Optional[UUID]:
        if not thread_id:
            return None
        try:
            return UUID(thread_id)
        except Exception:
            return None

    def _get_thread_if_owned(self, thread_repo: ThreadRepository, thread_id: Optional[str], user_id: UUID) -> Optional[Thread]:
        thread_uuid = self._parse_thread_id(thread_id)
        if not thread_uuid:
            return None
        return thread_repo.find_owned(thread_uuid, user_id)

    def get_thread_if_owned(self, thread_id: UUID, user_id: UUID) -> Optional[Thread]:
        """Get a thread only if it belongs to the given user."""
        with get_db_context() as session:
            thread_repo = ThreadRepository(session)
            return thread_repo.find_owned(thread_id, user_id)

    def update_thread(
        self,
        thread_id: UUID,
        user_id: UUID,
        title: Optional[str] = None,
        status: Optional[str] = None,
        is_starred: Optional[bool] = None,
        is_pinned: Optional[bool] = None,
    ) -> Optional[Thread]:
        """Update a thread if owned by user. Returns updated thread or None."""
        with get_db_context() as session:
            thread_repo = ThreadRepository(session)
            thread = thread_repo.find_owned(thread_id, user_id)
            if not thread:
                return None

            if title is not None:
                thread.title = title
            if status is not None:
                thread.status = ThreadStatus(status)
            if is_starred is not None:
                thread.is_starred = is_starred
            if is_pinned is not None:
                thread.is_pinned = is_pinned

            thread_repo.flush()
            return thread

    def ensure_thread(self, user_id: UUID, thread_id: Optional[str], title: Optional[str]) -> str:
        """Ensure a thread exists and return its ID."""
        with get_db_context() as session:
            thread_repo = ThreadRepository(session)
            if thread_id:
                existing = self._get_thread_if_owned(thread_repo, thread_id, user_id)
                if existing:
                    return str(existing.id)
                log_warning("Thread not found or not owned by user; creating new thread")

            new_thread = Thread(
                user_id=user_id,
                title=title or f"Chat {local_now().strftime('%Y%m%d_%H%M%S')}",
                status=ThreadStatus.ACTIVE,
            )
            thread_repo.create(new_thread)
            log_debug(f"Created thread {new_thread.id} for user {user_id}")
            return str(new_thread.id)

    def append_message_async(
        self,
        *,
        user_id: UUID,
        thread_id: Optional[str],
        role: MessageRole,
        content: str,
        run_id: Optional[str] = None,
        character_id: Optional[str] = None,
    ) -> None:
        """Persist a message asynchronously.

        IMPORTANT: `thread_id` should already be resolved via `ensure_thread()`
        before calling this method.  The async task will never create a new
        thread -- it only writes to the existing one.  If the thread cannot be
        found (e.g. deleted between calls) the message is silently dropped.
        """

        def _task():
            try:
                with get_db_context() as session:
                    thread_repo = ThreadRepository(session)
                    message_repo = MessageRepository(session)

                    thread_uuid = _parse_uuid(thread_id)
                    if thread_uuid is None:
                        log_warning(f"append_message_async: invalid thread_id={thread_id}, dropping message")
                        return

                    # Touch updated_at
                    existing_thread = thread_repo.find_by_id(thread_uuid)
                    if existing_thread is None:
                        log_warning(f"append_message_async: thread {thread_uuid} not found, dropping message")
                        return

                    # Auto-title from first user message
                    if role == MessageRole.USER:
                        if not existing_thread.title or existing_thread.title.startswith("Chat "):
                            existing_thread.title = _default_thread_title(content)

                    existing_thread.updated_at = utc_now()
                    thread_repo.flush()

                    message = Message(
                        thread_id=thread_uuid,
                        content=content,
                        role=role,
                        run_id=run_id,
                        character_id=character_id,
                    )
                    message_repo.create(message)

                    # Write-through to Redis hot window (best-effort).
                    if self._cache:
                        try:
                            self._cache.append_hot_message(
                                thread_id=str(thread_uuid),
                                role=role.value,
                                content=content,
                            )
                        except Exception:
                            pass

                    self._compact_if_needed(message_repo, thread_uuid)
            except Exception as e:
                log_warning(f"Async chat history write failed: {e}")

        _EXECUTOR.submit(_task)

    def list_threads(self, user_id: UUID, limit: int = 20) -> List[Thread]:
        """Return recent threads for a user."""
        with get_db_context() as session:
            thread_repo = ThreadRepository(session)
            return thread_repo.list_by_user(user_id=user_id, limit=limit)

    def hard_delete_thread(self, thread_id: UUID) -> bool:
        """Permanently delete thread and clear associated Redis cache."""
        with get_db_context() as session:
            thread_repo = ThreadRepository(session)
            thread = thread_repo.find_by_id(thread_id)
            if thread:
                thread_repo.hard_delete(thread)
                # Context manager will commit on exit -- no manual commit needed.

                # Clear stale Redis hot/warm data (best-effort).
                if self._cache:
                    try:
                        self._cache.clear_thread_cache(thread_id=str(thread_id))
                    except Exception:
                        pass

                return True
            return False

    def get_messages(self, thread_id: UUID, limit: int = 200) -> List[Message]:
        """Return messages for a thread."""
        with get_db_context() as session:
            message_repo = MessageRepository(session)
            return message_repo.find_by_thread(thread_id=thread_id, limit=limit, order_asc=True)

    def get_memory_buffer(self, thread_id: UUID, window_rounds: int = WINDOW_ROUNDS) -> List[ChatMessageRecord]:
        """Return a memory buffer for LLM: latest summary + last window rounds."""
        # Try Redis hot/warm first (fast path). Fallback to Postgres if missing.
        if self._cache:
            try:
                warm = self._cache.get_warm_summary(thread_id=str(thread_id))
                hot = self._cache.get_hot_messages(thread_id=str(thread_id))
                if hot:
                    buffer: List[ChatMessageRecord] = []
                    if warm and warm.summary:
                        buffer.append({"role": "assistant", "content": warm.summary})
                    user_seen = 0
                    selected: List[ChatMessageRecord] = []
                    for msg in reversed(hot):
                        if msg.role == "user":
                            user_seen += 1
                        if user_seen > window_rounds:
                            break
                        selected.append({"role": msg.role, "content": msg.content})
                    buffer.extend(reversed(selected))
                    return buffer
            except Exception:
                pass

        with get_db_context() as session:
            message_repo = MessageRepository(session)
            messages = message_repo.find_by_thread(thread_id=thread_id, limit=1000, order_asc=True)

        # Backfill Redis hot window (best-effort) if empty.
        if self._cache:
            try:
                if not self._cache.get_hot_messages(thread_id=str(thread_id)):
                    for m in messages[-500:]:
                        self._cache.append_hot_message(
                            thread_id=str(thread_id),
                            role=m.role.value,
                            content=m.content,
                        )
            except Exception:
                pass

        summary_message: Optional[Message] = None
        summary_text: Optional[str] = None
        for msg in reversed(messages):
            if self._is_summary_message(msg):
                summary_message = msg
                break

        if summary_message:
            cutoff_time = summary_message.created_at
            messages = [m for m in messages if not cutoff_time or (m.created_at and m.created_at > cutoff_time)]
        # No summary message exists -- this thread has never been compacted.
        # We simply continue without a summary prefix; the window-based
        # selection below will return the most recent messages.

        # Keep last window_rounds user messages (and their surrounding assistant/tool messages)
        buffer: List[ChatMessageRecord] = []
        if summary_message:
            summary_text = self._strip_summary_prefix(summary_message.content)

        if summary_text:
            buffer.append({"role": "assistant", "content": summary_text})
            # Cache warm summary (best-effort).
            if self._cache:
                try:
                    self._cache.set_warm_summary(thread_id=str(thread_id), summary=summary_text)
                except Exception:
                    pass

        user_seen = 0
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                user_seen += 1
            if user_seen > window_rounds:
                break
            buffer.append({"role": msg.role.value, "content": msg.content})

        return list(reversed(buffer))

    def _compact_if_needed(self, message_repo: MessageRepository, thread_id: UUID) -> None:
        """Summarize and compact when window exceeds threshold."""
        messages = message_repo.find_by_thread(thread_id=thread_id, limit=1000, order_asc=True)

        last_summary = None
        for msg in reversed(messages):
            if self._is_summary_message(msg):
                last_summary = msg
                break

        if last_summary:
            messages = [m for m in messages if m.created_at and m.created_at > last_summary.created_at]

        user_count = sum(1 for m in messages if m.role == MessageRole.USER)
        if user_count < WINDOW_ROUNDS:
            return

        # Select first WINDOW_ROUNDS user turns
        selected: List[Message] = []
        users = 0
        for msg in messages:
            selected.append(msg)
            if msg.role == MessageRole.USER:
                users += 1
                if users >= WINDOW_ROUNDS:
                    break

        summary_text = self._summarize_messages(selected)
        if not summary_text:
            return

        # Cache warm summary (Redis).
        if self._cache:
            try:
                self._cache.set_warm_summary(thread_id=str(thread_id), summary=summary_text)
            except Exception:
                pass

        summary_message = Message(
            thread_id=thread_id,
            content=f"{SUMMARY_PREFIX}\n{summary_text}",
            role=MessageRole.ASSISTANT,
        )
        message_repo.create(summary_message)

        # Delete summarized messages
        message_repo.delete_batch(selected)
        log_info(f"Compacted {len(selected)} messages into summary for thread {thread_id}")

    def _summarize_messages(self, messages: List[Message]) -> Optional[str]:
        if not messages:
            return None

        if not form.SELECTED_MODEL:
            return None

        if not form.SELECTED_MODEL.llm:
            form.SELECTED_MODEL.setup()

        parts = [
            "Summarize the following conversation in concise markdown. "
            "Capture decisions, facts, and unresolved questions."
        ]
        for msg in messages:
            parts.append(f"{msg.role.value.upper()}: {msg.content}")

        prompt = "\n".join(parts)
        try:
            response = form.SELECTED_MODEL.llm.invoke(prompt)
            return getattr(response, "content", str(response))
        except Exception as e:
            log_warning(f"Summary generation failed: {e}")
            return None

    def _is_summary_message(self, message: Message) -> bool:
        if message.role != MessageRole.ASSISTANT:
            return False
        content = message.content or ""
        return content.startswith(SUMMARY_PREFIX)

    def _strip_summary_prefix(self, content: str) -> str:
        if not content:
            return content
        if content.startswith(SUMMARY_PREFIX):
            return content[len(SUMMARY_PREFIX) :].lstrip()
        return content


chat_history_service = ChatHistoryService()
