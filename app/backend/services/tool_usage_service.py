"""
Tool usage logging service.
"""

from __future__ import annotations

import json
from contextvars import ContextVar
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from backend.db.session import get_db_context, get_engine
from backend.db.models.message import Message, MessageRole
from backend.db.models.thread import Thread
from backend.db.models.tool_usage import ToolStatus
from backend.db.repositories.tool_usage_repo import ToolUsageRepository
from backend.schemas.tool_usage import ToolUsageCreate
from backend.utils.log import log_debug


_TOOL_THREAD_ID: ContextVar[Optional[str]] = ContextVar("tool_thread_id", default=None)
_TOOL_RUN_ID: ContextVar[Optional[str]] = ContextVar("tool_run_id", default=None)


def set_tool_logging_context(*, thread_id: str, run_id: str) -> None:
    """
    Attach workflow identifiers to subsequent tool logs.
    """

    _TOOL_THREAD_ID.set(thread_id)
    _TOOL_RUN_ID.set(run_id)


def clear_tool_logging_context() -> None:
    """Clear tool logging context for the current run."""

    _TOOL_THREAD_ID.set(None)
    _TOOL_RUN_ID.set(None)


def _get_context_ids(
    *,
    thread_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    if thread_id is None:
        thread_id = _TOOL_THREAD_ID.get()
    if run_id is None:
        run_id = _TOOL_RUN_ID.get()

    return thread_id, run_id


def _safe_json_dumps(payload: Dict[str, Any]) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        # As a fallback, stringify the dict in a stable-ish way.
        return str(payload)


def _parse_uuid(value: Optional[str]) -> Optional[UUID]:
    if not value:
        return None
    try:
        return UUID(value)
    except Exception:
        return None


def _tables_exist() -> bool:
    try:
        engine = get_engine()
        inspector = inspect(engine)
        return inspector.has_table("thread") and inspector.has_table("message") and inspector.has_table("tool_usage")
    except Exception:
        return False


def log_tool_usage(
    *,
    tool_name: str,
    status: ToolStatus,
    input_data: Optional[Dict[str, Any]] = None,
    output_preview: str = "",
    error_message: Optional[str] = None,
    thread_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> None:
    """
    Persist a tool call
    """

    try:
        with get_db_context() as session:
            ToolUsageService.log_tool_usage(
                session,
                tool_name=tool_name,
                status=status,
                input_data=input_data,
                output_preview=output_preview,
                error_message=error_message,
                thread_id=thread_id,
                run_id=run_id,
            )
    except Exception as e:
        # Never break execution due to logging failures.
        log_debug(f"Tool usage logging skipped: {e}")
        return


class ToolUsageService:
    """
    Service for persisting tool usage logs.
    """

    @staticmethod
    def log_tool_usage(
        session: Session,
        *,
        tool_name: str,
        status: ToolStatus,
        input_data: Optional[Dict[str, Any]] = None,
        output_preview: str = "",
        error_message: Optional[str] = None,
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> None:
        if not tool_name:
            return

        if not _tables_exist():
            return

        ctx_thread_id, ctx_run_id = _get_context_ids(thread_id=thread_id, run_id=run_id)
        thread_uuid = _parse_uuid(ctx_thread_id)

        if thread_uuid is None:
            return

        payload = {
            "tool": tool_name,
            "status": getattr(status, "value", str(status)),
            "input": input_data or {},
            "output_preview": (output_preview or "")[:2000],
            "error": (error_message or "")[:2000] if error_message else None,
        }
        content = _safe_json_dumps(payload)

        try:
            # Only log if thread exists; we cannot create one without a user_id.
            thread = session.query(Thread).filter(Thread.id == thread_uuid).first()
            if not thread:
                return

            message = Message(
                thread_id=thread_uuid,
                role=MessageRole.TOOL,
                content=content,
                run_id=ctx_run_id,
            )
            session.add(message)
            session.flush()  # obtain message.id

            tool_usage_repo = ToolUsageRepository(session)
            tool_usage_repo.create(
                ToolUsageCreate(
                    tool_name=tool_name,
                    status=status,
                    error_message=error_message,
                ),
                message_id=message.id,
            )
        except Exception as e:
            log_debug(f"Tool usage logging skipped: {e}")
            return


tool_usage_service = ToolUsageService()
