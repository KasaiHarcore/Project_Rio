"""Tests for tool error fallback."""

from langchain_core.messages import AIMessage, ToolMessage

from workflows.utils.tool_fallback import tool_error_fallback


def test_single_tool_call():
    ai_msg = AIMessage(
        content="",
        tool_calls=[{"id": "tc_1", "name": "web_search", "args": {}}],
    )
    result = tool_error_fallback({"error": "timeout", "messages": [ai_msg]})
    msgs = result["messages"]
    assert len(msgs) == 1
    assert isinstance(msgs[0], ToolMessage)
    assert msgs[0].tool_call_id == "tc_1"
    assert "timeout" in msgs[0].content


def test_parallel_tool_calls():
    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {"id": "tc_1", "name": "web_search", "args": {}},
            {"id": "tc_2", "name": "recall_memories", "args": {}},
            {"id": "tc_3", "name": "search_documents", "args": {}},
        ],
    )
    result = tool_error_fallback({"error": "crash", "messages": [ai_msg]})
    msgs = result["messages"]
    assert len(msgs) == 3
    ids = {m.tool_call_id for m in msgs}
    assert ids == {"tc_1", "tc_2", "tc_3"}


def test_no_tool_calls():
    ai_msg = AIMessage(content="just text")
    result = tool_error_fallback({"error": "oops", "messages": [ai_msg]})
    msgs = result["messages"]
    assert len(msgs) == 1
    assert msgs[0].tool_call_id == "unknown"
