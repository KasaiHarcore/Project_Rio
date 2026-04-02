"""Note Confirmation endpoints: resume workflow after HITL interrupt.

Provides the resume endpoint that the frontend calls when a user
approves or rejects a pending note operation (delete / full-rewrite).
The response uses the same Vercel AI SDK data-stream protocol as the
chat endpoint so the frontend can merge tokens and events seamlessly.
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.dependencies import get_current_user
from workflows.executor import resume_note_confirmation
from core.settings import AgentConfig
from models.user import User
from utils.log import log_info, log_error


router = APIRouter(prefix="/note-confirmation", tags=["note-confirmation"])


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


class NoteConfirmationResumeRequest(BaseModel):
    """Body sent by the frontend when user responds to a note confirmation card."""
    thread_id: str = Field(..., description="Thread with the pending note confirmation")
    decision: str = Field(..., description="User decision: approve | reject")
    mode: Optional[str] = Field("chat", description="Agent mode")
    character: Optional[str] = Field("rio", description="Persona ID")


@router.post("/resume")
async def resume_note(
    body: NoteConfirmationResumeRequest,
    user: User = Depends(get_current_user),
):
    """Resume the workflow after a note confirmation decision.

    Returns a streaming response using the AI SDK data-stream protocol,
    identical to the chat endpoint, so the frontend can merge tokens
    and structured events into the existing message list.
    """
    log_info(
        f"[REST] note-confirmation/resume: user={user.username} "
        f"thread={body.thread_id} decision={body.decision}"
    )

    config = AgentConfig(
        mode=body.mode or "chat",
        character=body.character or "rio",
        user_role=user.role.value,
    )

    def _generate():
        answer_parts: list[str] = []
        try:
            for event in resume_note_confirmation(
                thread_id=body.thread_id,
                config=config,
                decision=body.decision,
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
                    decision_data = event.get("decision", {})
                    yield _data_line({
                        "type": "supervisor_decision",
                        "action": decision_data.get("action"),
                        "worker": decision_data.get("next_worker"),
                        "reasoning": decision_data.get("reasoning", ""),
                    })

                elif event_type == "worker":
                    yield _data_line({
                        "type": "worker_result",
                        "worker": event.get("worker"),
                        "success": event.get("success"),
                        "content_preview": event.get("content_preview", ""),
                    })

                elif event_type == "note_result":
                    yield _data_line({
                        "type": "note_result",
                        "action": event.get("action"),
                        "notes": event.get("notes", []),
                        "persisted_ids": event.get("persisted_ids", []),
                    })

                elif event_type == "note_confirmation_request":
                    yield _data_line({
                        "type": "note_confirmation_request",
                        "confirmation_type": event.get("confirmation_type"),
                        "note_id": event.get("note_id", ""),
                        "note_title": event.get("note_title", ""),
                        "action": event.get("action", "delete"),
                        "message": event.get("message", ""),
                        "options": event.get("options", ["approve", "reject"]),
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
                        "decision": result.get("decision"),
                    })

                elif event_type == "error":
                    yield _error_line(event.get("error", "Unknown error"))

        except Exception as exc:
            log_error(f"Note confirmation streaming error: {exc}")
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
