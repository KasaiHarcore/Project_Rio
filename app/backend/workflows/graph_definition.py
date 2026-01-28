"""LangGraph definition and construction utilities."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict, Annotated
from uuid import UUID

from langchain_core.messages import (
	AIMessage,
	BaseMessage,
	HumanMessage,
	SystemMessage,
	ToolMessage,
)
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from backend.services.llm import form
from backend.schemas.query import ChatMessageRecord


class GraphState(TypedDict, total=False):
	"""State for LangGraph agent workflow."""
	schema_version: int
	# The only checkpointed channel we rely on for resume/time-travel.
	messages: Annotated[List[BaseMessage], add_messages]


def build_config_payload(
	*,
	thread_id: str | UUID,
	checkpoint_id: Optional[str] = None,
	checkpoint_ns: str = "",
) -> Dict[str, Any]:
	"""Build a RunnableConfig payload for checkpointing."""
	if not thread_id:
		raise ValueError("thread_id is required for LangGraph checkpointing")
	configurable: Dict[str, Any] = {
		"thread_id": str(thread_id),
		"checkpoint_ns": checkpoint_ns or "",
	}
	if checkpoint_id:
		configurable["checkpoint_id"] = checkpoint_id
	return {"configurable": configurable}


def build_messages(
	*,
	question: str,
	history: Optional[List[ChatMessageRecord]],
) -> List[BaseMessage]:
	"""Construct LangChain messages for the agent."""
	messages: List[BaseMessage] = []
	for item in history or []:
		role = (item or {}).get("role", "user")
		content = (item or {}).get("content", "")
		if not content:
			continue
		if role == "assistant":
			messages.append(AIMessage(content=content))
		elif role == "tool":
			messages.append(ToolMessage(content=content, tool_call_id="tool"))
		else:
			messages.append(HumanMessage(content=content))
	messages.append(HumanMessage(content=question))
	return messages


def extract_answer(messages: List[BaseMessage]) -> str:
	"""Extract the most recent assistant message."""
	for msg in reversed(messages or []):
		if isinstance(msg, AIMessage):
			return msg.content or ""
	return ""


def extract_tool_context(messages: List[BaseMessage]) -> str:
	"""Collect tool outputs into a single context string."""
	chunks: List[str] = []
	for msg in messages or []:
		if isinstance(msg, ToolMessage) and msg.content:
			content = str(msg.content).strip()
			if content:
				chunks.append(content)
	return "\n\n".join(chunks).strip()


def should_use_tools(state: GraphState) -> str:
	"""Route to tools if the agent emitted tool calls."""
	messages = state.get("messages") or []
	if not messages:
		return END
	last = messages[-1]
	tool_calls = getattr(last, "tool_calls", None)
	if tool_calls:
		return "tools"
	return END


def build_graph(
	*,
	tools: List[Any],
	system_prompt: str,
	checkpointer: Any | None,
	) -> StateGraph:
	"""Create a LangGraph workflow with tool execution loop."""

	llm = form.SELECTED_MODEL.llm
	llm_with_tools = llm.bind_tools(tools) if tools else llm

	def _select_messages(state: GraphState) -> List[BaseMessage]:
		messages = state.get("messages", [])
		if system_prompt:
			return [SystemMessage(content=system_prompt)] + messages
		return messages

	def _wrap_response(response: BaseMessage) -> Dict[str, Any]:
		return {"messages": [response]}

	agent_node = (
		RunnableLambda(_select_messages)
		| llm_with_tools
		| RunnableLambda(_wrap_response)
	)

	graph = StateGraph(GraphState)
	graph.add_node("agent", agent_node)
	if tools:
		graph.add_node("tools", ToolNode(tools))

	graph.add_edge(START, "agent")

	if tools:
		graph.add_conditional_edges("agent", should_use_tools, {"tools": "tools", END: END})
		graph.add_edge("tools", "agent")
	else:
		graph.add_edge("agent", END)

	return graph.compile(checkpointer=checkpointer) if checkpointer else graph.compile()
