"""Tool error fallback for graceful handling of tool execution failures.

When a ToolNode raises an exception, this fallback returns error
ToolMessages for ALL pending tool_calls in the last AIMessage. This is
critical for parallel tool calls — without it, orphaned tool_call_ids
cause API 400 errors on the next LLM invocation.
"""

from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import ToolMessage

from utils.log import log_warning


def tool_error_fallback(error_state: Dict[str, Any]) -> Dict[str, Any]:
    """Create error ToolMessages for every pending tool_call.

    Args:
        error_state: Dict with ``"error"`` (exception text) and
            ``"messages"`` (current message list).

    Returns:
        Dict with ``"messages"`` containing one ToolMessage per
        pending tool_call, each reporting the error.
    """
    error_msg = f"Error executing tool: {error_state.get('error', 'Unknown error')}"
    log_warning(f"[ToolFallback] {error_msg}")

    messages_list = error_state.get("messages", [])
    tool_calls = []
    if messages_list:
        last_msg = messages_list[-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            tool_calls = last_msg.tool_calls

    if not tool_calls:
        return {
            "messages": [ToolMessage(content=error_msg, tool_call_id="unknown")]
        }

    return {
        "messages": [
            ToolMessage(
                content=error_msg,
                tool_call_id=(
                    tc.get("id", "unknown")
                    if isinstance(tc, dict)
                    else getattr(tc, "id", "unknown")
                ),
            )
            for tc in tool_calls
        ]
    }
