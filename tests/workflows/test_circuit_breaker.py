"""Tests for circuit breaker and max tool rounds."""

from langchain_core.messages import HumanMessage, ToolMessage

from workflows.utils.circuit_breaker import check_circuit_breaker, check_max_tool_rounds


def _tool(content: str, i: int = 0) -> ToolMessage:
    return ToolMessage(content=content, tool_call_id=f"tc_{i}")


def test_circuit_breaker_identical_messages():
    msgs = [_tool("same error", i) for i in range(4)]
    assert check_circuit_breaker(msgs, window=4) is True


def test_circuit_breaker_varying_content():
    msgs = [_tool(f"error {i}", i) for i in range(4)]
    assert check_circuit_breaker(msgs, window=4) is False


def test_circuit_breaker_below_window():
    msgs = [_tool("same error", i) for i in range(3)]
    assert check_circuit_breaker(msgs, window=4) is False


def test_circuit_breaker_ignores_non_tool_messages():
    msgs = [
        HumanMessage(content="hi"),
        _tool("same error", 0),
        _tool("same error", 1),
        _tool("same error", 2),
        _tool("same error", 3),
    ]
    assert check_circuit_breaker(msgs, window=4) is True


def test_max_tool_rounds_above_limit():
    msgs = [HumanMessage(content="hi")]
    msgs += [_tool("result", i) for i in range(10)]
    assert check_max_tool_rounds(msgs, max_rounds=10) is True


def test_max_tool_rounds_below_limit():
    msgs = [HumanMessage(content="hi")]
    msgs += [_tool("result", i) for i in range(5)]
    assert check_max_tool_rounds(msgs, max_rounds=10) is False


def test_max_tool_rounds_counts_after_last_human():
    msgs = [
        _tool("old result", 0),
        _tool("old result", 1),
        _tool("old result", 2),
        HumanMessage(content="new question"),
        _tool("new result", 3),
    ]
    # Only 1 tool message after the HumanMessage
    assert check_max_tool_rounds(msgs, max_rounds=3) is False
