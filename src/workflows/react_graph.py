"""ReAct agent graph with Planner layer.

Replaces the prebuilt ``create_react_agent`` with a custom graph that adds:
- **Planner**: pre-analyzes user intent, selects tools, generates instruction
- **Dual tool registry**: brief descriptions (planner) + detailed guides (agent)
- **Circuit breaker**: detects repeated identical tool failures
- **Max tool rounds**: configurable limit on tool execution loops
- **Tool error fallback**: graceful handling of tool execution failures
- **Default skills**: prompt-only routing for gestures/out_of_scope/abusive

Preserved from the original architecture:
- Deterministic input/output guardrails
- Post-processing (memory storage, emotional engine)
- Delegation to sub-agents (mission, note, sql, os)
- Emotional engine + persona system
- PostgresStore long-term memory
"""

from __future__ import annotations

import os
import threading
from textwrap import dedent
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.store.base import BaseStore

from core.settings import AgentConfig
from infrastructure.llm import form
from utils.log import log_debug, log_info, log_warning

from workflows.default_skills import SKILL_NAMES
from workflows.planner import planner_node
from workflows.react_prompt import build_system_prompt, build_dynamic_prompt_section
from workflows.react_state import ReactAgentState
from workflows.tool_registry import build_selected_guides, build_tool_registry, ToolRegistryEntry
from workflows.tools import build_supervisor_tools
from workflows.utils.circuit_breaker import check_circuit_breaker, check_max_tool_rounds
from workflows.utils.message_utils import trim_messages_with_integrity, truncate_ai_messages
from workflows.utils.tool_fallback import tool_error_fallback

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

REACT_RECURSION_LIMIT = int(os.getenv("REACT_AGENT_RECURSION_LIMIT", "30"))
MAX_TOOL_ROUNDS = int(os.getenv("REACT_MAX_TOOL_ROUNDS", "10"))
CIRCUIT_BREAKER_WINDOW = int(os.getenv("REACT_CIRCUIT_BREAKER_WINDOW", "4"))
MAX_CONTEXT_MESSAGES = int(os.getenv("REACT_MAX_CONTEXT_MESSAGES", "12"))

# ---------------------------------------------------------------------------
# Guardrail nodes (deterministic only — no LLM calls)
# ---------------------------------------------------------------------------


def _input_guardrail_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic input guardrail: length check only."""
    from workflows.guardrails.input_guardrail import _check_input_length

    messages = state.get("messages") or []
    text = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            text = msg.content
            break

    passed, reason = _check_input_length(text)
    if not passed:
        log_warning(f"[InputGuardrail] Rejected: {reason}")
    return {
        "guardrail_passed": passed if not passed else True,
        "guardrail_rejection": reason if not passed else None,
    }


def _output_guardrail_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic output guardrail: PII + system leak regex only."""
    from workflows.guardrails.output_guardrail import _check_pii, _check_system_leak

    messages = state.get("messages") or []
    text = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            text = msg.content
            break

    if not text:
        return {"guardrail_output_passed": True, "guardrail_output_rejection": None}

    for check_fn in (_check_pii, _check_system_leak):
        passed, reason = check_fn(text)
        if not passed:
            log_warning(f"[OutputGuardrail] Rejected: {reason}")
            return {"guardrail_output_passed": False, "guardrail_output_rejection": reason}

    return {"guardrail_output_passed": True, "guardrail_output_rejection": None}


def _guardrail_reject_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Return a safe rejection message."""
    from workflows.guardrails.rejection import (
        _INPUT_REJECTION_MESSAGE,
        _OUTPUT_REJECTION_MESSAGE,
    )

    if state.get("guardrail_passed") is False:
        msg = _INPUT_REJECTION_MESSAGE
    elif state.get("guardrail_output_passed") is False:
        msg = _OUTPUT_REJECTION_MESSAGE
    else:
        msg = _INPUT_REJECTION_MESSAGE

    return {
        "messages": [AIMessage(content=msg)],
        "status": "completed",
    }


# ---------------------------------------------------------------------------
# Post-process node (background tasks)
# ---------------------------------------------------------------------------


def _post_process_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fire background tasks: memory storage, emotional engine."""
    messages = state.get("messages") or []
    user_id = state.get("user_id")
    character_id = state.get("character_id", "rio")
    thread_id = state.get("thread_id")

    question = ""
    response = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            question = msg.content
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            response = msg.content
            break

    if user_id and question and response:
        snapshot = {
            "user_id": user_id,
            "original_question": question,
            "thread_id": thread_id,
            "mode": state.get("mode", "chat"),
            "metadata": {"character": character_id},
        }
        thread = threading.Thread(
            target=_run_background_tasks,
            args=(snapshot, response),
            daemon=True,
        )
        thread.start()

    return {"status": "completed"}


def _run_background_tasks(state_snapshot: Dict[str, Any], response: str) -> None:
    """Background: memory storage + emotional engine update."""
    user_id = state_snapshot.get("user_id")
    question = state_snapshot.get("original_question", "")
    character_id = (state_snapshot.get("metadata") or {}).get("character", "rio")

    # 1. Store episodic memory
    if user_id and question and response and len(response) > 20:
        try:
            from workflows.memory_store import store_memory, memory_store_context
            from uuid import uuid4

            mode = state_snapshot.get("mode", "chat")
            summary = f"[{mode}] Q: {question[:200]} A: {response[:400]}"

            with memory_store_context() as bg_store:
                store_memory(
                    bg_store,
                    user_id=user_id,
                    memory_key=f"interaction_{uuid4().hex[:8]}",
                    text=summary,
                    memory_type="episodic",
                    metadata={
                        "thread_id": state_snapshot.get("thread_id"),
                        "mode": mode,
                    },
                )
                log_debug(f"Stored episodic memory for user {user_id}")
        except Exception as e:
            log_warning(f"[PostProcess] Memory storage failed: {e}")

    # 2. Update emotional engine
    if user_id:
        try:
            from infrastructure.database import get_db_context
            from services.emotional_engine import EmotionalEngine
            from repositories.emotional_state_repository import EmotionalStateRepository

            uid = UUID(user_id) if isinstance(user_id, str) else user_id
            with get_db_context() as db:
                engine = EmotionalEngine(EmotionalStateRepository(db))
                sentiment = engine.analyze_sentiment(question)
                engine.record_interaction(
                    user_id=uid,
                    character_id=character_id,
                    sentiment=sentiment,
                    task_success=None,
                    context=question[:200],
                )
        except Exception as e:
            log_warning(f"[PostProcess] Emotional engine update failed: {e}")


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------


def _route_after_input_guardrail(state: Dict[str, Any]) -> str:
    if state.get("guardrail_passed", True):
        return "planner"
    return "guardrail_reject"


def _route_after_input_guardrail_no_planner(state: Dict[str, Any]) -> str:
    if state.get("guardrail_passed", True):
        return "agent"
    return "guardrail_reject"


def _route_after_output_guardrail(state: Dict[str, Any]) -> str:
    if state.get("guardrail_output_passed", True):
        return END
    return "guardrail_reject"


# ---------------------------------------------------------------------------
# Agent node (replaces prebuilt create_react_agent)
# ---------------------------------------------------------------------------


def _build_agent_node(
    llm: Any,
    tools: list,
    static_prompt: str,
    registry: Dict[str, ToolRegistryEntry],
    enable_planner: bool,
):
    """Factory: create the main agent node function with captured dependencies."""

    def agent_node(state: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Main ReAct agent — calls the LLM with planner-selected tool guides."""
        messages = state.get("messages") or []
        if not messages:
            return {"messages": [AIMessage(content="Hello Sensei! How can I help you today?")]}

        instruction = state.get("instruction") or ""
        actions: list = state.get("actions") or []

        # ── Trim and compress history ──
        try:
            trimmed = trim_messages_with_integrity(messages, max_messages=MAX_CONTEXT_MESSAGES)
            trimmed = truncate_ai_messages(trimmed, max_words=20)
        except Exception:
            trimmed = messages

        # ── Build system message ──
        system_parts = [static_prompt]

        if enable_planner and actions:
            # Planner is active: inject only selected tool guides
            is_skill_only = all(a in SKILL_NAMES for a in actions)

            if not is_skill_only:
                guides_block = build_selected_guides(actions, registry)
                if guides_block:
                    system_parts.append(guides_block)

            if instruction:
                system_parts.append(f"## INSTRUCTION\n{instruction}")

            system_parts.append(_EXECUTION_GUIDANCE)
        else:
            # Planner disabled or no actions: inject legacy TOOL_INSTRUCTIONS
            system_parts.append(build_dynamic_prompt_section(
                instruction=instruction,
                actions=actions,
                registry=registry,
                mode=state.get("mode", "chat"),
            ))

        system_content = "\n\n---\n\n".join(system_parts)
        system_message = SystemMessage(content=system_content)

        # ── Decide whether to bind tools ──
        is_skill_only = enable_planner and actions and all(a in SKILL_NAMES for a in actions)

        if is_skill_only:
            # Prompt-only skill: invoke WITHOUT tools
            response = llm.invoke([system_message] + list(trimmed))
        elif tools:
            model_with_tools = llm.bind_tools(tools)
            response = model_with_tools.invoke([system_message] + list(trimmed))
        else:
            response = llm.invoke([system_message] + list(trimmed))

        return {"messages": [response]}

    return agent_node


_EXECUTION_GUIDANCE = dedent("""\
    ## EXECUTION FLOW

    1. **Route by action type:**
       - If actions are `out_of_scope` / `gestures` / `abusive`
         -> No tool calls. Generate a direct response based on the instruction.
       - If actions include tool names -> proceed to step 2.

    2. **Call tools based on instruction:**
       - Use the strategy hint (parallel / sequential / iterative).
       - When no hint: parallel if independent, sequential if one feeds another.

    3. **After tool results — EVALUATE before responding:**
       - Sufficient? -> Synthesize and respond.
       - New targets found? -> Call additional tools (ANY available, not just selected).
       - Tool error? -> Try alternative tool. Do NOT retry same tool with same args.

    4. **Response rules:**
       - ALWAYS cite specific names, paths, sources from tool output.
       - When combining multiple tool results, explicitly connect them.
       - Respond in the same language as the user's message.
""").strip()


# ---------------------------------------------------------------------------
# should_continue routing
# ---------------------------------------------------------------------------


def _build_should_continue(max_tool_rounds: int, circuit_breaker_window: int):
    """Factory: create the should_continue routing function."""

    def should_continue(state: Dict[str, Any]) -> str:
        """Route to 'tools' or 'end' based on tool calls and safety checks."""
        messages = state.get("messages") or []
        if not messages:
            return "end"

        last_message = messages[-1]
        if not (hasattr(last_message, "tool_calls") and last_message.tool_calls):
            return "end"

        # Circuit breaker: repeated identical failures
        if check_circuit_breaker(messages, window=circuit_breaker_window):
            return "end"

        # Max tool rounds
        if check_max_tool_rounds(messages, max_rounds=max_tool_rounds):
            return "end"

        return "tools"

    return should_continue


# ---------------------------------------------------------------------------
# Context fetchers
# ---------------------------------------------------------------------------


def _fetch_emotional_context(user_id: str, character_id: str) -> Dict[str, str]:
    """Fetch emotional context from the engine (best-effort)."""
    try:
        from infrastructure.database import get_db_context
        from services.emotional_engine import EmotionalEngine
        from repositories.emotional_state_repository import EmotionalStateRepository

        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        with get_db_context() as db:
            engine = EmotionalEngine(EmotionalStateRepository(db))
            return engine.compute_emotional_context(uid, character_id)
    except Exception as e:
        log_warning(f"[ReactGraph] Failed to fetch emotional context: {e}")
        return {}


def _fetch_memories(store: Optional[BaseStore], user_id: str, question: str) -> List[Dict]:
    """Fetch relevant long-term memories (best-effort)."""
    if not store or not user_id:
        return []
    try:
        from workflows.memory_store import search_memories

        return search_memories(store, user_id=user_id, query=question, limit=5)
    except Exception as e:
        log_warning(f"[ReactGraph] Failed to fetch memories: {e}")
        return []


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_react_graph(
    *,
    config: AgentConfig,
    checkpointer=None,
    store: Optional[BaseStore] = None,
    user_id: Optional[str] = None,
    question: str = "",
) -> CompiledStateGraph:
    """Build the complete ReAct agent graph.

    When ``config.enable_planner`` is True (default):
        START -> input_guardrail -> planner -> agent <-> tools -> post_process -> output_guardrail -> END

    When ``config.enable_planner`` is False (fallback, identical to old behavior):
        START -> input_guardrail -> agent <-> tools -> post_process -> output_guardrail -> END
    """
    user_id = user_id or ""
    user_role = config.user_role or "user"
    character_id = config.character or "rio"
    enable_planner = config.enable_planner

    # ── Fetch context for system prompt ──
    emotional_ctx = _fetch_emotional_context(user_id, character_id) if user_id else {}
    memories = _fetch_memories(store, user_id, question) if user_id else []

    # ── Build static system prompt (identity + persona + safety + mode) ──
    static_prompt = build_system_prompt(
        character_id=character_id,
        emotional_ctx=emotional_ctx,
        memories=memories,
        mode=config.mode or "chat",
    )

    # ── Build tool registry ──
    registry = build_tool_registry(user_role)

    # ── Build supervisor tools (direct + delegation) ──
    tools = build_supervisor_tools(
        user_id=user_id,
        user_role=user_role,
        config=config,
        store=store,
    )

    # ── Ensure LLM is initialized ──
    if not form.SELECTED_MODEL or not getattr(form.SELECTED_MODEL, "llm", None):
        if form.SELECTED_MODEL:
            form.SELECTED_MODEL.setup()

    llm = form.SELECTED_MODEL.llm

    # ── Build tool node with fallback ──
    tool_node = ToolNode(tools)
    tool_node_with_fallback = tool_node.with_fallbacks(
        [RunnableLambda(tool_error_fallback)],
        exception_key="error",
    )

    # ── Build node functions ──
    agent_fn = _build_agent_node(
        llm=llm,
        tools=tools,
        static_prompt=static_prompt,
        registry=registry,
        enable_planner=enable_planner,
    )
    should_continue_fn = _build_should_continue(
        max_tool_rounds=MAX_TOOL_ROUNDS,
        circuit_breaker_window=CIRCUIT_BREAKER_WINDOW,
    )

    # ── Build outer graph ──
    outer = StateGraph(ReactAgentState)

    outer.add_node("input_guardrail", _input_guardrail_node)
    if enable_planner:
        outer.add_node("planner", planner_node)
    outer.add_node("agent", agent_fn)
    outer.add_node("tools", tool_node_with_fallback)
    outer.add_node("post_process", _post_process_node)
    outer.add_node("output_guardrail", _output_guardrail_node)
    outer.add_node("guardrail_reject", _guardrail_reject_node)

    # ── Edges ──
    outer.add_edge(START, "input_guardrail")

    if enable_planner:
        outer.add_conditional_edges("input_guardrail", _route_after_input_guardrail)
        outer.add_edge("planner", "agent")
    else:
        outer.add_conditional_edges("input_guardrail", _route_after_input_guardrail_no_planner)

    outer.add_conditional_edges("agent", should_continue_fn, {"tools": "tools", "end": "post_process"})
    outer.add_edge("tools", "agent")
    outer.add_edge("post_process", "output_guardrail")
    outer.add_conditional_edges("output_guardrail", _route_after_output_guardrail)
    outer.add_edge("guardrail_reject", END)

    compiled = outer.compile(
        checkpointer=checkpointer,
        store=store,
    )

    # Store config on graph for executor to access
    compiled._rio_config = {
        "tool_registry": registry,
        "planner_llm": llm,
    }

    log_info(
        f"[ReactGraph] Built graph: {len(tools)} tools, "
        f"planner={'ON' if enable_planner else 'OFF'}, "
        f"mode={config.mode}, role={user_role}, persona={character_id}"
    )
    return compiled
