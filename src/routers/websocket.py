"""WebSocket endpoints: real-time bidirectional chat.

Protocol:
1. Client connects to ``/ws/chat``
2. Client sends auth message:  ``{"type": "auth", "token": "eyJ..."}``
3. Server validates token and sends: ``{"type": "auth_ok", "user_id": "..."}``
4. Client sends chat messages:
   ``{"type": "message", "content": "...", "thread_id": "...", "mode": "chat", "character": "rio"}``
5. Server streams responses using the same event types as the REST chat endpoint:
   ``{"type": "token", "content": "..."}``
   ``{"type": "supervisor_decision", ...}``
   ``{"type": "final", ...}``
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.ws_manager import ws_manager
from infrastructure.security.auth import decode_token
from utils.log import log_info, log_error, log_warning

router = APIRouter(tags=["websocket"])

# Auth timeout: client must send auth within this many seconds
_AUTH_TIMEOUT_SECONDS = 10


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Real-time bidirectional chat via WebSocket.

    Flow:
    1. Accept connection
    2. Wait for auth message with JWT token
    3. Validate token
    4. Enter message loop: receive user messages, stream AI responses
    """
    user_id: Optional[str] = None

    try:
        # Accept the raw connection first (before auth)
        await websocket.accept()

        # ── Step 1: Authenticate ────────────────────────────────────────
        try:
            raw = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=_AUTH_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            await websocket.send_json({
                "type": "error",
                "message": "Authentication timeout — send auth message within 10 seconds",
            })
            await websocket.close(code=4001, reason="Auth timeout")
            return

        try:
            auth_msg = json.loads(raw)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "error", "message": "Invalid JSON"})
            await websocket.close(code=4002, reason="Invalid JSON")
            return

        if auth_msg.get("type") != "auth" or not auth_msg.get("token"):
            await websocket.send_json({
                "type": "error",
                "message": "First message must be: {\"type\": \"auth\", \"token\": \"...\"}",
            })
            await websocket.close(code=4003, reason="Auth required")
            return

        token_data = decode_token(auth_msg["token"])
        if token_data is None:
            await websocket.send_json({"type": "error", "message": "Invalid or expired token"})
            await websocket.close(code=4004, reason="Invalid token")
            return

        user_id = token_data.user_id
        log_info(f"[WS] Authenticated: user={user_id}")

        # Register with manager (don't call accept again — already accepted)
        async with ws_manager._lock:
            ws_manager._connections.setdefault(user_id, []).append(websocket)

        await websocket.send_json({
            "type": "auth_ok",
            "user_id": user_id,
            "message": "Authenticated successfully",
        })

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(ws_manager.heartbeat(websocket, interval=30))

        # ── Step 2: Message loop ────────────────────────────────────────
        try:
            while True:
                raw = await websocket.receive_text()

                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                    continue

                msg_type = msg.get("type")

                if msg_type == "pong":
                    # Client responding to heartbeat — ignore
                    continue

                if msg_type == "message":
                    content = msg.get("content", "").strip()
                    if not content:
                        await websocket.send_json({"type": "error", "message": "Empty message"})
                        continue

                    thread_id = msg.get("thread_id")
                    mode = msg.get("mode", "chat")
                    character = msg.get("character", "rio")

                    # Process the chat message using AgentService
                    await _handle_chat_message(
                        websocket=websocket,
                        user_id=user_id,
                        content=content,
                        thread_id=thread_id,
                        mode=mode,
                        character=character,
                    )
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    })

        except WebSocketDisconnect:
            log_info(f"[WS] Client disconnected: user={user_id}")
        finally:
            heartbeat_task.cancel()

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log_error(f"[WS] Unexpected error: {exc}")
    finally:
        if user_id:
            await ws_manager.disconnect(user_id, websocket)


async def _handle_chat_message(
    websocket: WebSocket,
    user_id: str,
    content: str,
    thread_id: Optional[str],
    mode: str,
    character: str,
) -> None:
    """Process a chat message and stream the response over WebSocket."""
    from services.agent_service import AgentService
    from services.chat_history_service import chat_history_service
    from core.settings import AgentConfig
    from models.message import MessageRole
    from core.concurrency import concurrency_manager

    # Resolve / create thread
    thread_id = chat_history_service.ensure_thread(
        user_id=user_id,
        thread_id=thread_id,
        title=content[:60],
    )

    await websocket.send_json({
        "type": "thread_resolved",
        "thread_id": thread_id,
    })

    config = AgentConfig(
        mode=mode,
        character=character,
        user_role="user",  # WebSocket users default to "user" role
    )

    # Persist user message
    chat_history_service.append_message_async(
        user_id=user_id,
        thread_id=thread_id,
        role=MessageRole.USER,
        content=content,
    )

    # Stream AI response
    answer_parts: list[str] = []
    run_id = None

    try:
        # Run the agent in a thread (it's sync/generator-based)
        def _stream_events():
            return list(AgentService().stream_query(
                question=content,
                config=config,
                history=[],
                thread_id=thread_id,
                user_id=user_id,
            ))

        events = await concurrency_manager.run_in_thread(_stream_events)

        for event in events:
            event_type = event.get("type")

            if event_type == "token":
                chunk = event.get("content", "")
                answer_parts.append(chunk)
                await websocket.send_json({"type": "token", "content": chunk})

            elif event_type == "run_started":
                run_id = event.get("run_id")
                await websocket.send_json({
                    "type": "run_started",
                    "run_id": run_id,
                    "thread_id": event.get("thread_id"),
                    "character": character,
                })

            elif event_type in ("supervisor", "worker", "planning", "note_result",
                                "artifact_result", "mission_result", "emotional_update",
                                "sql_approval_request"):
                await websocket.send_json(event)

            elif event_type == "final":
                result = event.get("result", {})
                run_id = event.get("run_id") or run_id
                final_answer = result.get("answer", "")
                if not answer_parts and final_answer:
                    answer_parts.append(final_answer)
                    await websocket.send_json({"type": "token", "content": final_answer})

                await websocket.send_json({
                    "type": "final",
                    "run_id": run_id,
                    "stats": result.get("stats", {}),
                    "thread_id": thread_id,
                })

            elif event_type == "error":
                await websocket.send_json({
                    "type": "error",
                    "message": event.get("error", "Unknown error"),
                })

    except Exception as exc:
        log_error(f"[WS] Chat error: {exc}")
        await websocket.send_json({
            "type": "error",
            "message": f"Processing error: {str(exc)}",
        })

    # Persist assistant message
    full_answer = "".join(answer_parts)
    if full_answer:
        chat_history_service.append_message_async(
            user_id=user_id,
            thread_id=thread_id,
            role=MessageRole.ASSISTANT,
            content=full_answer,
            run_id=run_id,
            character_id=character,
        )

    # Signal completion
    await websocket.send_json({"type": "done", "thread_id": thread_id})
