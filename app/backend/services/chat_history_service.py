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
from backend.utils.log import log_debug, log_info, log_warning
from backend.services.llm import form
from backend.schemas.query import ChatMessageRecord


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
        with get_db_context() as session:
            repo = MessageRepository(session)
            messages = repo.get_by_thread(thread_id, skip=0, limit=1000)

        summary = None
        for msg in reversed(messages):
            if self._is_summary_message(msg):
                summary = msg
                break

        if summary:
            cutoff_time = summary.created_at
            messages = [m for m in messages if not cutoff_time or (m.created_at and m.created_at > cutoff_time)]

        # Keep last window_rounds user messages (and their surrounding assistant/tool messages)
        buffer: List[ChatMessageRecord] = []
        if summary:
            buffer.append({"role": "assistant", "content": self._strip_summary_prefix(summary.content)})

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
