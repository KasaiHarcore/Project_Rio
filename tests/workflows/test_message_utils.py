"""Tests for message trimming and truncation utilities."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from workflows.utils.message_utils import (
    trim_messages_with_integrity,
    truncate_ai_messages,
    _ensure_tool_call_integrity,
)


def test_trim_within_limit():
    msgs = [HumanMessage(content=f"msg {i}") for i in range(5)]
    result = trim_messages_with_integrity(msgs, max_messages=12)
    assert len(result) == 5


def test_trim_exceeding_limit():
    msgs = [HumanMessage(content=f"msg {i}") for i in range(20)]
    result = trim_messages_with_integrity(msgs, max_messages=8)
    assert len(result) <= 10  # roughly 8, may be slightly more due to integrity


def test_tool_call_integrity_reinserts_missing():
    ai_msg = AIMessage(
        content="Calling tools",
        tool_calls=[
            {"id": "tc_1", "name": "web_search", "args": {}},
            {"id": "tc_2", "name": "recall_memories", "args": {}},
        ],
    )
    tool_1 = ToolMessage(content="result 1", tool_call_id="tc_1")
    tool_2 = ToolMessage(content="result 2", tool_call_id="tc_2")

    # Simulate trimming that kept ai_msg + tool_1 but dropped tool_2
    trimmed = [ai_msg, tool_1]
    original = [ai_msg, tool_1, tool_2]

    result = _ensure_tool_call_integrity(trimmed, original)
    tool_ids = {m.tool_call_id for m in result if isinstance(m, ToolMessage)}
    assert "tc_2" in tool_ids


def test_truncate_long_content():
    long_content = " ".join(f"word{i}" for i in range(50))
    msgs = [AIMessage(content=long_content)]
    result = truncate_ai_messages(msgs, max_words=20)
    assert result[0].content.endswith("...")
    # "..." is appended to the 20th word, so split gives 20 tokens
    words = result[0].content.split()
    assert len(words) == 20
    assert words[-1].endswith("...")


def test_truncate_preserves_pending_tool_calls():
    long_content = " ".join(f"word{i}" for i in range(50))
    ai_msg = AIMessage(
        content=long_content,
        tool_calls=[{"id": "tc_1", "name": "web_search", "args": {}}],
    )
    # No matching ToolMessage => tool calls are pending
    msgs = [ai_msg]
    result = truncate_ai_messages(msgs, max_words=20)
    # Should NOT be truncated (pending tool calls)
    assert not result[0].content.endswith("...")


def test_truncate_short_content_untouched():
    msgs = [AIMessage(content="short text")]
    result = truncate_ai_messages(msgs, max_words=20)
    assert result[0].content == "short text"
