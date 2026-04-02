"""Circuit breaker and max-tool-rounds checks for the ReAct agent loop.

These prevent infinite loops when tools repeatedly fail or return
identical results.
"""

from __future__ import annotations

from typing import Any, List

from langchain_core.messages import HumanMessage, ToolMessage

from utils.log import log_info


def check_circuit_breaker(messages: List[Any], window: int = 4) -> bool:
    """Return True if the last *window* ToolMessages have identical content.

    This detects the pattern where the agent keeps retrying the same tool
    call and getting the same error, creating an infinite loop.
    """
    recent_tool_msgs = [
        m for m in reversed(messages) if isinstance(m, ToolMessage)
    ][:window]

    if len(recent_tool_msgs) < window:
        return False

    contents = [m.content for m in recent_tool_msgs]
    if len(set(contents)) == 1:
        log_info(
            f"[CircuitBreaker] Last {window} tool messages are identical, breaking loop"
        )
        return True
    return False


def check_max_tool_rounds(
    messages: List[Any],
    max_rounds: int = 10,
) -> bool:
    """Return True if the number of ToolMessages since the last HumanMessage >= *max_rounds*.

    Counts backward from the end of the message list until a HumanMessage
    is found, tallying ToolMessages along the way.
    """
    tool_count = 0
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            break
        if isinstance(msg, ToolMessage):
            tool_count += 1

    if tool_count >= max_rounds:
        log_info(f"[MaxToolRounds] Reached {tool_count}/{max_rounds} tool rounds, breaking loop")
        return True
    return False
