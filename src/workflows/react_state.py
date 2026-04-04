"""Simplified state for the ReAct agent graph.

The ReAct pattern uses ``messages`` as the primary data channel — tool results
flow as ToolMessage objects in the message list rather than separate state fields.
"""

from __future__ import annotations

from typing import Annotated, List, Optional, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ReactAgentState(TypedDict, total=False):
    """State schema for the ReAct agent workflow.

    Only ``messages`` is required by the LangGraph agent loop.
    All other fields are metadata set once at initialization.
    """

    # ── Core (required by LangGraph ReAct) ──
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # ── Metadata (set once at init, immutable during agent run) ──
    thread_id: str
    user_id: Optional[str]
    user_role: str          # "user" | "admin"
    character_id: str       # persona id, e.g. "rio"
    mode: str               # hint only: "chat" | "rag" | "web" | "sql"

    # ── Planner output (set by planner node, consumed by agent node) ──
    instruction: Optional[str]       # Focused instruction from planner
    actions: Optional[List[str]]     # Selected tool names from planner

    # ── Guardrails ──
    guardrail_passed: Optional[bool]
    guardrail_rejection: Optional[str]
    guardrail_output_passed: Optional[bool]
    guardrail_output_rejection: Optional[str]

    # ── Tracking ──
    status: str             # "running" | "completed" | "failed" | "waiting_human"
