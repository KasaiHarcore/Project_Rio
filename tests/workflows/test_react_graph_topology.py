"""Tests for ReAct graph routing functions."""

from langchain_core.messages import AIMessage, HumanMessage

from workflows.react_graph import (
    _route_after_input_guardrail,
    _route_after_input_guardrail_no_planner,
    _route_after_output_guardrail,
    _build_should_continue,
)


def test_input_guardrail_routes_to_planner_on_pass():
    assert _route_after_input_guardrail({"guardrail_passed": True}) == "planner"


def test_input_guardrail_routes_to_reject_on_fail():
    assert _route_after_input_guardrail({"guardrail_passed": False}) == "guardrail_reject"


def test_input_guardrail_no_planner_routes_to_agent():
    assert _route_after_input_guardrail_no_planner({"guardrail_passed": True}) == "agent"


def test_output_guardrail_routes_to_end_on_pass():
    result = _route_after_output_guardrail({"guardrail_output_passed": True})
    assert result == "__end__"


def test_output_guardrail_routes_to_reject_on_fail():
    assert _route_after_output_guardrail({"guardrail_output_passed": False}) == "guardrail_reject"


def test_should_continue_ends_on_empty():
    fn = _build_should_continue(max_tool_rounds=10, circuit_breaker_window=4)
    assert fn({"messages": []}) == "end"


def test_should_continue_ends_on_no_tool_calls():
    fn = _build_should_continue(max_tool_rounds=10, circuit_breaker_window=4)
    msgs = [HumanMessage(content="hi"), AIMessage(content="Hello!")]
    assert fn({"messages": msgs}) == "end"


def test_should_continue_routes_to_tools():
    fn = _build_should_continue(max_tool_rounds=10, circuit_breaker_window=4)
    ai_msg = AIMessage(
        content="",
        tool_calls=[{"id": "tc_1", "name": "web_search", "args": {}}],
    )
    msgs = [HumanMessage(content="search for X"), ai_msg]
    assert fn({"messages": msgs}) == "tools"
