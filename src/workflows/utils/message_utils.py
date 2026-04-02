"""Message trimming with tool-call integrity preservation.

Prevents API 400 errors when parallel tool calls get partially trimmed
by ensuring every AIMessage with tool_calls has ALL its ToolMessage
responses present in the trimmed output.
"""

from __future__ import annotations

from typing import Any, List

from langchain_core.messages import AIMessage, ToolMessage, trim_messages

from utils.log import log_info, log_warning


def trim_messages_with_integrity(
    messages: List[Any],
    max_messages: int = 12,
) -> List[Any]:
    """Trim message history while preserving tool-call integrity.

    Uses LangChain's ``trim_messages`` with ``strategy="last"`` to keep
    recent messages, then repairs any orphaned tool_calls by re-inserting
    missing ToolMessages from the original history.

    Args:
        messages: Full message list.
        max_messages: Maximum number of messages to retain (counted by len).

    Returns:
        Trimmed message list with tool-call pairs intact.
    """
    if len(messages) <= max_messages:
        return messages

    try:
        trimmed = trim_messages(
            messages,
            max_tokens=max_messages,
            token_counter=len,
            strategy="last",
            start_on="human",
            end_on=("human", "tool"),
            include_system=True,
            allow_partial=False,
        )
        return _ensure_tool_call_integrity(trimmed, messages)
    except Exception as exc:
        log_warning(f"[MessageUtils] trim_messages failed, keeping all: {exc}")
        return messages


def _ensure_tool_call_integrity(
    trimmed: List[Any],
    original: List[Any],
) -> List[Any]:
    """Re-insert missing ToolMessages for parallel tool calls.

    When the LLM makes parallel tool calls (tool_calls list > 1), trimming
    can remove some ToolMessages while keeping the AIMessage, causing an
    API 400 error ("tool_call_id did not have response messages").
    """
    original_tool_messages: dict = {}
    for msg in original:
        if isinstance(msg, ToolMessage) and hasattr(msg, "tool_call_id"):
            original_tool_messages[msg.tool_call_id] = msg

    trimmed_tool_ids = {
        msg.tool_call_id
        for msg in trimmed
        if isinstance(msg, ToolMessage) and hasattr(msg, "tool_call_id")
    }

    result: List[Any] = []
    for msg in trimmed:
        result.append(msg)
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                tc_id = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
                if tc_id and tc_id not in trimmed_tool_ids and tc_id in original_tool_messages:
                    result.append(original_tool_messages[tc_id])
                    trimmed_tool_ids.add(tc_id)
                    log_info(f"[MessageUtils] Re-inserted ToolMessage for tool_call_id={tc_id}")

    return result


def truncate_ai_messages(messages: List[Any], max_words: int = 20) -> List[Any]:
    """Truncate historical AIMessage content to save context window space.

    Only truncates AIMessages whose tool_calls have ALL been executed
    (matching ToolMessages exist). Never truncates AIMessages with
    pending tool_calls.
    """
    if not messages:
        return messages

    executed_tool_call_ids = {
        msg.tool_call_id
        for msg in messages
        if isinstance(msg, ToolMessage) and getattr(msg, "tool_call_id", None)
    }

    result: List[Any] = []
    for msg in messages:
        if not isinstance(msg, AIMessage):
            result.append(msg)
            continue

        has_tool_calls = bool(getattr(msg, "tool_calls", None))

        if has_tool_calls:
            all_executed = all(
                (tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None))
                in executed_tool_call_ids
                for tc in msg.tool_calls
            )
            if not all_executed:
                result.append(msg)
                continue

        content = msg.content
        if isinstance(content, str) and content.strip():
            words = content.split()
            if len(words) > max_words:
                truncated_content = " ".join(words[:max_words]) + "..."
                truncated_msg = AIMessage(content=truncated_content)
                if has_tool_calls:
                    truncated_msg.tool_calls = msg.tool_calls
                if hasattr(msg, "id"):
                    truncated_msg.id = msg.id
                result.append(truncated_msg)
            else:
                result.append(msg)
        else:
            result.append(msg)

    return result
