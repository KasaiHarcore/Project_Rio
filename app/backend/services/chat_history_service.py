"""Chat history service for SQL-backed message persistence."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
import os

from backend.db.session import get_db_context
from backend.db.models.thread import Thread, ThreadStatus
from backend.db.models.message import Message, MessageRole
from backend.db.repositories.thread_repo import ThreadRepository
from backend.db.repositories.message_repo import MessageRepository
from backend.db.models.agent_memory import MemoryType
from backend.services.memory_service import memory_service
from backend.utils.log import log_debug, log_info, log_warning
from backend.services.llm import form
from backend.schemas.query import ChatMessageRecord
from backend.cache import cache_service


_EXECUTOR = ThreadPoolExecutor(max_workers=2)
WINDOW_ROUNDS = int(os.getenv("CHAT_HISTORY_WINDOW_ROUNDS", "20"))
RETENTION_DAYS = int(os.getenv("CHAT_HISTORY_RETENTION_DAYS", "7"))
SUMMARY_PREFIX = "[SUMMARY]"


def _default_thread_title(content: str) -> str:
    cleaned = " ".join((content or "").strip().split())
    return cleaned[:60] if cleaned else f"Chat {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"


class ChatHistoryService:
    """Service to persist and retrieve chat history."""

    @staticmethod
    def _parse_thread_id(thread_id: Optional[str]) -> Optional[UUID]:
        if not thread_id:
            return None
        try:
            return UUID(thread_id)
        except Exception:
            return None

    @staticmethod
    def _get_thread_if_owned(session, thread_id: Optional[str], user_id: UUID) -> Optional[Thread]:
        thread_uuid = ChatHistoryService._parse_thread_id(thread_id)
        if not thread_uuid:
            return None
        thread = session.query(Thread).filter(Thread.id == thread_uuid, Thread.user_id == user_id).first()
        return thread

    def ensure_thread(self, user_id: UUID, thread_id: Optional[str], title: Optional[str]) -> str:
        """Ensure a thread exists and return its ID."""
        with get_db_context() as session:
            thread_repo = ThreadRepository(session)
            if thread_id:
                existing = self._get_thread_if_owned(session, thread_id, user_id)
                if existing:
                    return str(existing.id)
                log_warning("Thread not found or not owned by user; creating new thread")

            new_thread = Thread(
                user_id=user_id,
                title=title or f"Chat {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                status=ThreadStatus.ACTIVE,
            )
            session.add(new_thread)
            session.flush()
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
    ) -> None:
        """Persist a message asynchronously."""

        def _task():
            try:
                with get_db_context() as session:
                    thread_repo = ThreadRepository(session)
                    message_repo = MessageRepository(session)

                    thread_uuid = None
                    existing = self._get_thread_if_owned(session, thread_id, user_id)
                    if existing:
                        thread_uuid = existing.id

                    if thread_uuid is None:
                        new_thread = Thread(
                            user_id=user_id,
                            title=_default_thread_title(content),
                            status=ThreadStatus.ACTIVE,
                        )
                        session.add(new_thread)
                        session.flush()
                        thread_uuid = new_thread.id

                    if role == MessageRole.USER:
                        existing_thread = thread_repo.get_by_id(thread_uuid)
                        if existing_thread and (not existing_thread.title or existing_thread.title.startswith("Chat ")):
                            existing_thread.title = _default_thread_title(content)
                            session.flush()

                    existing_thread = thread_repo.get_by_id(thread_uuid)
                    if existing_thread:
                        existing_thread.updated_at = datetime.utcnow()
                        session.flush()

                    message = Message(
                        thread_id=thread_uuid,
                        content=content,
                        role=role,
                        run_id=run_id,
                    )
                    session.add(message)

                    if role in (MessageRole.USER, MessageRole.ASSISTANT):
                        memory_service.add_agent_memory(
                            session=session,
                            user_id=user_id,
                            thread_id=thread_uuid,
                            run_id=run_id,
                            memory_type=MemoryType.LONG_TERM,
                            content=content,
                        )

                    # Write-through to Redis hot window (best-effort).
                    try:
                        cache_service.append_hot_message(
                            thread_id=str(thread_uuid),
                            role=role.value,
                            content=content,
                        )
                    except Exception:
                        pass

                    self._compact_if_needed(session, thread_uuid)
                    self._cleanup_expired(session)
            except Exception as e:
                log_warning(f"Async chat history write failed: {e}")

        _EXECUTOR.submit(_task)

    def list_threads(self, user_id: UUID, limit: int = 20) -> List[Thread]:
        """Return recent threads for a user."""
        with get_db_context() as session:
            repo = ThreadRepository(session)
            return repo.get_by_user(user_id, skip=0, limit=limit)

    def hard_delete_thread(self, thread_id: UUID) -> bool:
        """Permanently delete thread (admin action)."""
        with get_db_context() as session:
            repo = ThreadRepository(session)
            return repo.delete(thread_id)

    def get_messages(self, thread_id: UUID, limit: int = 200) -> List[Message]:
        """Return messages for a thread."""
        with get_db_context() as session:
            repo = MessageRepository(session)
            return repo.get_by_thread(thread_id, skip=0, limit=limit)

    def get_memory_buffer(self, thread_id: UUID, window_rounds: int = WINDOW_ROUNDS) -> List[ChatMessageRecord]:
        """Return a memory buffer for LLM: latest summary + last window rounds."""
        # Try Redis hot/warm first (fast path). Fallback to Postgres if missing.
        try:
            warm = cache_service.get_warm_summary(thread_id=str(thread_id))
            hot = cache_service.get_hot_messages(thread_id=str(thread_id))
            if hot:
                buffer: List[ChatMessageRecord] = []
                if warm and warm.summary:
                    buffer.append({"role": "assistant", "content": warm.summary})
                # Keep last window_rounds user messages (and their surrounding assistant/tool messages)
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
            repo = MessageRepository(session)
            messages = repo.get_by_thread(thread_id, skip=0, limit=1000)

        # Backfill Redis hot window (best-effort) if empty.
        try:
            if not cache_service.get_hot_messages(thread_id=str(thread_id)):
                for m in messages[-500:]:
                    cache_service.append_hot_message(
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
        else:
            summary_text = memory_service.get_thread_summary(thread_id=thread_id)

        # Keep last window_rounds user messages (and their surrounding assistant/tool messages)
        buffer: List[ChatMessageRecord] = []
        if summary_message:
            summary_text = self._strip_summary_prefix(summary_message.content)

        if summary_text:
            buffer.append({"role": "assistant", "content": summary_text})
            # Cache warm summary (best-effort).
            try:
                cache_service.set_warm_summary(thread_id=str(thread_id), summary=summary_text)
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

    def _compact_if_needed(self, session, thread_id: UUID) -> None:
        """Summarize and compact when window exceeds threshold."""
        repo = MessageRepository(session)
        messages = repo.get_by_thread(thread_id, skip=0, limit=1000)

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
        memory_service.upsert_thread_summary(
            session=session,
            thread_id=thread_id,
            summary=summary_text,
        )
        try:
            thread = session.query(Thread).filter(Thread.id == thread_id).first()
            if thread and thread.user_id:
                memory_service.add_agent_memory(
                    session=session,
                    user_id=thread.user_id,
                    thread_id=thread_id,
                    run_id=None,
                    memory_type=MemoryType.SUMMARY,
                    content=summary_text,
                )
        except Exception:
            pass
        # Cache warm summary immediately (best-effort).
        try:
            cache_service.set_warm_summary(thread_id=str(thread_id), summary=summary_text)
        except Exception:
            pass

        summary_message = Message(
            thread_id=thread_id,
            content=f"{SUMMARY_PREFIX}\n{summary_text}",
            role=MessageRole.ASSISTANT,
        )
        session.add(summary_message)
        session.flush()

        # Delete summarized messages
        for msg in selected:
            session.delete(msg)
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

    @staticmethod
    def _is_summary_message(message: Message) -> bool:
        if message.role != MessageRole.ASSISTANT:
            return False
        content = message.content or ""
        return content.startswith(SUMMARY_PREFIX)

    @staticmethod
    def _strip_summary_prefix(content: str) -> str:
        if not content:
            return content
        if content.startswith(SUMMARY_PREFIX):
            return content[len(SUMMARY_PREFIX) :].lstrip()
        return content

    def _cleanup_expired(self, session) -> None:
        cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
        session.query(Message).filter(Message.created_at < cutoff).delete(synchronize_session=False)


chat_history_service = ChatHistoryService()
