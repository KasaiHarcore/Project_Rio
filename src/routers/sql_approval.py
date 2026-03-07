"""SQL Approval endpoints: resume workflow after HITL interrupt.

Provides the resume endpoint that the frontend calls when a user
approves, edits, or rejects a pending SQL operation.  The response
uses the same Vercel AI SDK data-stream protocol as the chat endpoint
so the frontend can pipe tokens and structured events seamlessly.
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.dependencies import get_current_user, get_db, require_admin
from workflows.executor import resume_sql_approval
from core.settings import AgentConfig
from models.user import User
from utils.log import log_info, log_error


router = APIRouter(prefix="/sql-approval", tags=["sql-approval"])


# ── Data-stream protocol helpers (shared with chat.py) ─────────────

def _text_line(chunk: str) -> str:
    return f"0:{json.dumps(chunk)}\n"


def _data_line(payload: list | dict) -> str:
    if isinstance(payload, dict):
        payload = [payload]
    return f"2:{json.dumps(payload)}\n"


def _finish_line(reason: str = "stop") -> str:
    return f'd:{json.dumps({"finishReason": reason})}\n'


def _error_line(message: str) -> str:
    return f'e:{json.dumps({"finishReason": "error", "message": message})}\n'


# ── Request schema ─────────────────────────────────────────────────

class SQLApprovalResumeRequest(BaseModel):
    """Body sent by the frontend when user responds to an SQL approval card."""
    thread_id: str = Field(..., description="Thread with the pending SQL approval")
    action: str = Field(
        ...,
        description="User action: approve | edit | reject | always_approve",
    )
    edited_sql: Optional[str] = Field(None, description="Modified SQL (required when action='edit')")
    reason: Optional[str] = Field(None, description="Optional rejection/edit reason")
    mode: Optional[str] = Field("sql", description="Agent mode (usually 'sql')")
    character: Optional[str] = Field("rio", description="Persona ID")


# ── Resume endpoint ───────────────────────────────────────────────

@router.post("/resume")
async def resume_sql(
    body: SQLApprovalResumeRequest,
    user: User = Depends(require_admin),
):
    """Resume the workflow after an SQL approval decision.

    Returns a streaming response using the AI SDK data-stream protocol,
    identical to the chat endpoint, so the frontend can merge tokens
    and structured events into the existing message list.
    """
    log_info(
        f"[REST] sql-approval/resume: user={user.username} "
        f"thread={body.thread_id} action={body.action}"
    )

    config = AgentConfig(
        mode=body.mode or "sql",
        character=body.character or "rio",
        user_role=user.role.value,
    )

    approval_response = {
        "action": body.action,
        "edited_sql": body.edited_sql,
        "reason": body.reason,
    }

    def _generate():
        answer_parts: list[str] = []
        try:
            for event in resume_sql_approval(
                thread_id=body.thread_id,
                config=config,
                approval_response=approval_response,
            ):
                event_type = event.get("type")

                if event_type == "token":
                    chunk = event.get("content", "")
                    answer_parts.append(chunk)
                    yield _text_line(chunk)

                elif event_type == "run_started":
                    yield _data_line({
                        "type": "run_started",
                        "run_id": event.get("run_id"),
                        "thread_id": event.get("thread_id"),
                    })

                elif event_type == "supervisor":
                    decision = event.get("decision", {})
                    yield _data_line({
                        "type": "supervisor_decision",
                        "action": decision.get("action"),
                        "worker": decision.get("next_worker"),
                        "reasoning": decision.get("reasoning", ""),
                    })

                elif event_type == "worker":
                    yield _data_line({
                        "type": "worker_result",
                        "worker": event.get("worker"),
                        "success": event.get("success"),
                        "content_preview": event.get("content_preview", ""),
                    })

                elif event_type == "sql_approval_request":
                    yield _data_line({
                        "type": "sql_approval_request",
                        "request_id": event.get("request_id"),
                        "sql": event.get("sql"),
                        "natural_query": event.get("natural_query"),
                        "operation_type": event.get("operation_type"),
                        "danger_level": event.get("danger_level"),
                        "affected_tables": event.get("affected_tables", []),
                        "estimated_rows_affected": event.get("estimated_rows_affected"),
                        "warnings": event.get("warnings", []),
                        "explanation": event.get("explanation", ""),
                        "message": event.get("message", ""),
                    })

                elif event_type == "final":
                    result = event.get("result", {})
                    final_answer = result.get("answer", "")
                    if not answer_parts and final_answer:
                        answer_parts.append(final_answer)
                        yield _text_line(final_answer)

                    yield _data_line({
                        "type": "final",
                        "run_id": event.get("run_id"),
                        "stats": _safe_stats(result.get("stats")),
                        "worker_results": result.get("worker_results", []),
                        "timing": result.get("timing", {}),
                        "approval_action": result.get("approval_action"),
                    })

                elif event_type == "error":
                    yield _error_line(event.get("error", "Unknown error"))

        except Exception as exc:
            log_error(f"SQL approval streaming error: {exc}")
            yield _error_line(str(exc))

        yield _finish_line("stop")

    return StreamingResponse(
        _generate(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Thread-Id": body.thread_id,
            "X-Vercel-AI-Data-Stream": "v1",
            "Cache-Control": "no-cache",
            "Transfer-Encoding": "chunked",
        },
    )


def _safe_stats(stats: dict | None) -> dict:
    if not stats:
        return {}
    return {
        "total_tokens": stats.get("total_tokens", 0),
        "total_input_tokens": stats.get("total_input_tokens", 0),
        "total_output_tokens": stats.get("total_output_tokens", 0),
        "total_cost": stats.get("total_cost", 0),
    }
