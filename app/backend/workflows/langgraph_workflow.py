"""LangGraph workflow for query execution."""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from uuid import uuid4
import time
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from langgraph.errors import GraphInterrupt
from psycopg_pool import ConnectionPool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.agents import create_agent

from backend.services.agent_service import AgentService
from backend.services.llm import form
from backend.core.settings import AgentConfig, get_app_config
from backend.services.run_service import run_service
from backend.services.workflow_state_service import resolve_checkpoint_thread_id
from backend.db.models.run import RunStatus
from backend.schemas.query import ChatMessageRecord
from backend.utils.log import log_error, log_warning
from backend.workflows.planner import run_planner
from backend.workflows.reflection import run_reflection


class GraphState(TypedDict, total=False):
    question: str
    config: AgentConfig
    history: List[ChatMessageRecord]
    thread_id: Optional[str]
    run_id: str
    step: int
    answer: str
    plan: Optional[str]
    reflection_notes: Optional[str]
    stats: Dict[str, Any]
    error: Optional[str]
    verify_passed: bool
    retry_count: int
    max_retries: int
    active_mode: Optional[str]
    rerun_mode: Optional[str]
    state_schema_version: int
    checkpoint_every: int
    state_scope: str
    started_at: Optional[float]
    deadline_ts: Optional[float]


_CHECKPOINTER = None
_CHECKPOINTER_READY = False

_HISTORY_ROLES = {"user", "assistant", "tool"}


def _normalize_pg_url(db_url: str) -> str:
    if db_url.startswith("postgresql+psycopg2://"):
        return db_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    return db_url


def _get_checkpointer():
    global _CHECKPOINTER, _CHECKPOINTER_READY
    if _CHECKPOINTER is not None:
        return _CHECKPOINTER

    app_config = get_app_config()
    db_url = app_config.database_url
    if db_url:
        try:
            pool = ConnectionPool(_normalize_pg_url(db_url), kwargs={"autocommit": True})
            saver = PostgresSaver(pool)
            if not _CHECKPOINTER_READY:
                saver.setup()
                _CHECKPOINTER_READY = True
            _CHECKPOINTER = saver
            return _CHECKPOINTER
        except Exception as e:
            log_warning(f"Postgres checkpointer unavailable, falling back to in-memory: {e}")

    _CHECKPOINTER = InMemorySaver()
    return _CHECKPOINTER


def _sanitize_history(
    history: Optional[List[Dict[str, Any]]],
    *,
    max_items: int,
) -> List[ChatMessageRecord]:
    if not history:
        return []

    cleaned: List[ChatMessageRecord] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in _HISTORY_ROLES:
            continue
        if not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue
        cleaned.append({"role": role, "content": content})

    if max_items and len(cleaned) > max_items:
        cleaned = cleaned[-max_items:]

    return cleaned


def _persist(node_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    step = int(state.get("step", 0)) + 1
    updated = {**state, "step": step}
    if "tools" in updated:
        updated.pop("tools", None)

    config = updated.get("config")
    if config is not None and not getattr(config, "enable_persistence", True):
        return updated

    checkpoint_every = int(updated.get("checkpoint_every", 1) or 1)
    if checkpoint_every < 1:
        checkpoint_every = 1

    if node_name != "finalize" and step % checkpoint_every != 0:
        return updated
    return updated


def _prepare(state: GraphState) -> GraphState:
    updated = _persist("prepare", state)
    return updated


def _route(state: GraphState) -> GraphState:
    question = state["question"]
    config = state["config"]
    active_mode = state.get("rerun_mode") or config.mode
    updated = {
        **state,
        "active_mode": active_mode,
        "rerun_mode": None,
    }
    updated = _persist("route", updated)
    return updated


def _plan(state: GraphState) -> GraphState:
    question = state.get("question", "")
    mode = state.get("active_mode") or getattr(state.get("config"), "mode", "rag")
    try:
        plan = run_planner(question=question, mode=mode)
        updated = {**state, "plan": plan}
        return _persist("plan", updated)
    except Exception as e:
        log_warning(f"Planner step failed: {e}")
        updated = {**state, "plan": None}
        return _persist("plan", updated)


def _run_agent(state: GraphState) -> GraphState:
    question = state["question"]
    history = state.get("history") or []
    config = state.get("config")
    tools = AgentService._get_tools(question, config)
    active_mode = state.get("active_mode") or getattr(config, "mode", "chat")
    system_prompt = AgentService._get_system_prompt(active_mode)

    deadline_ts = state.get("deadline_ts")
    if deadline_ts and time.time() > float(deadline_ts):
        error_msg = "Execution deadline exceeded before agent run."
        updated = {**state, "error": error_msg}
        return _persist("run_agent", updated)

    try:
        messages = []
        for msg in history[-10:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "user":
                messages.append(HumanMessage(content=content))

        messages.append(HumanMessage(content=question))

        config = state.get("config")
        max_retries = int(getattr(config, "model_max_retries", 2) if config else 2)
        backoff_base = float(getattr(config, "model_backoff_base", 0.5) if config else 0.5)
        backoff_max = float(getattr(config, "model_backoff_max", 4.0) if config else 4.0)

        last_error = None
        for attempt in range(max_retries + 1):
            if deadline_ts and time.time() > float(deadline_ts):
                raise RuntimeError("Execution deadline exceeded during agent run.")
            try:
                agent = create_agent(form.SELECTED_MODEL.llm, tools=tools, system_prompt=system_prompt)
                result = agent.invoke({"messages": messages})
                output_messages = result.get("messages", [])
                answer = getattr(output_messages[-1], "content", "") if output_messages else ""
                if not answer:
                    answer = "No response generated. Please try rephrasing your question."
                answer = form.format_markdown_output(answer)
                stats = form.SELECTED_MODEL.get_overall_exec_stats()
                updated = {
                    **state,
                    "answer": answer,
                    "stats": stats,
                    "error": None,
                }
                updated = _persist("run_agent", updated)
                return updated
            except GraphInterrupt:
                raise
            except Exception as e:
                last_error = e
                if attempt >= max_retries:
                    break
                sleep_time = min(backoff_max, backoff_base * (2 ** attempt))
                time.sleep(sleep_time)

        error_msg = f"Agent execution failed after retries: {last_error}"
        log_error(error_msg)
        updated = {**state, "error": error_msg}
        updated = _persist("run_agent", updated)
        return updated
    except GraphInterrupt:
        raise
    except Exception as e:
        error_msg = f"Agent execution failed: {e}"
        log_error(error_msg)
        updated = {**state, "error": error_msg}
        updated = _persist("run_agent", updated)
        return updated


def _verify(state: GraphState) -> GraphState:
    question = state.get("question", "")
    answer = state.get("answer", "")
    mode = getattr(state.get("config"), "mode", "rag")
    retry_count = int(state.get("retry_count", 0))
    max_retries = int(state.get("max_retries", 2))

    deadline_ts = state.get("deadline_ts")
    if deadline_ts and time.time() > float(deadline_ts):
        error_msg = "Execution deadline exceeded before verify."
        updated = {**state, "error": error_msg, "verify_passed": False}
        return _persist("verify", updated)

    if not answer.strip():
        updated = {
            **state,
            "verify_passed": False,
            "retry_count": retry_count + 1,
        }
        return _persist("verify", updated)

    verify_system_prompt = (
        "You are a strict verifier. Validate the assistant answer against the question. "
        "Reply with 'VALID' if correct, grounded, and consistent; otherwise reply with 'INVALID'."
    )

    try:
        if state.get("config") and getattr(state.get("config"), "enable_reflection", False):
            try:
                reflection_notes = run_reflection(question=question, answer=answer)
                state = {**state, "reflection_notes": reflection_notes}
            except Exception as e:
                log_warning(f"Reflection step failed: {e}")

        messages = [
            SystemMessage(content=verify_system_prompt),
            HumanMessage(content=f"Question: {question}\nMode: {mode}\nAnswer: {answer}"),
        ]

        config = state.get("config")
        max_retries_model = int(getattr(config, "model_max_retries", 2) if config else 2)
        backoff_base = float(getattr(config, "model_backoff_base", 0.5) if config else 0.5)
        backoff_max = float(getattr(config, "model_backoff_max", 4.0) if config else 4.0)

        last_error = None
        response = None
        for attempt in range(max_retries_model + 1):
            if deadline_ts and time.time() > float(deadline_ts):
                raise RuntimeError("Execution deadline exceeded during verify.")
            try:
                response = form.SELECTED_MODEL.llm.invoke(messages)
                break
            except Exception as e:
                last_error = e
                if attempt >= max_retries_model:
                    break
                sleep_time = min(backoff_max, backoff_base * (2 ** attempt))
                time.sleep(sleep_time)

        if response is None:
            raise RuntimeError(f"Verify LLM call failed after retries: {last_error}")

        content = (getattr(response, "content", "") or "").strip().upper()
        is_valid = content.startswith("VALID")

        updated = {
            **state,
            "verify_passed": is_valid,
            "retry_count": retry_count + (0 if is_valid else 1),
            "rerun_mode": state.get("active_mode") if not is_valid else None,
        }

        if not is_valid and updated["retry_count"] > max_retries:
            updated["error"] = f"Verification failed after {max_retries} retries."

        return _persist("verify", updated)
    except Exception as e:
        error_msg = f"Verify step failed: {e}"
        log_warning(error_msg)
        updated = {
            **state,
            "verify_passed": False,
            "retry_count": retry_count + 1,
            "error": error_msg,
            "rerun_mode": state.get("active_mode"),
        }
        return _persist("verify", updated)


def _finalize(state: GraphState) -> GraphState:
    if state.get("error"):
        updated = _persist("finalize", state)
        raise RuntimeError(updated["error"])
    updated = _persist("finalize", state)
    return updated


def build_workflow() -> StateGraph:
    graph = StateGraph(GraphState)
    graph.add_node("prepare", _prepare)
    graph.add_node("route", _route)
    graph.add_node("plan", _plan)
    graph.add_node("run_agent", _run_agent)
    graph.add_node("verify", _verify)
    graph.add_node("finalize", _finalize)
    graph.set_entry_point("prepare")
    graph.add_edge("prepare", "route")
    graph.add_conditional_edges(
        "route",
        lambda s: "plan" if getattr(s.get("config"), "enable_planner", False) else "run_agent",
        {"plan": "plan", "run_agent": "run_agent"},
    )
    graph.add_edge("plan", "run_agent")
    graph.add_edge("run_agent", "verify")
    graph.add_conditional_edges(
        "verify",
        lambda s: "finalize"
        if s.get("verify_passed") or s.get("error") or s.get("retry_count", 0) > s.get("max_retries", 2)
        else "run_agent",
        {"finalize": "finalize", "run_agent": "run_agent"},
    )
    graph.add_edge("finalize", END)
    return graph


def run_workflow(
    *,
    question: str,
    config: AgentConfig,
    history: Optional[List[Dict[str, Any]]] = None,
    thread_id: Optional[str] = None,
    run_id: Optional[str] = None,
    resume: Optional[bool] = None,
) -> Dict[str, Any]:
    graph = build_workflow().compile(checkpointer=_get_checkpointer())
    run_id = run_id or uuid4().hex
    checkpoint_thread_id = resolve_checkpoint_thread_id(
        thread_id,
        run_id,
        getattr(config, "state_scope", None),
    )
    config_payload = {"configurable": {"thread_id": checkpoint_thread_id}}

    max_history_items = int(getattr(config, "history_max_items", 50) or 0)
    sanitized_history = _sanitize_history(history, max_items=max_history_items)

    if resume is not None:
        result = graph.invoke(Command(resume=resume), config=config_payload)
        result["run_id"] = result.get("run_id", run_id)
        if "__interrupt__" not in result:
            run_service.finish_run(run_id=result["run_id"], status=RunStatus.SUCCEEDED)
        return result

    state: GraphState = {
        "question": question,
        "config": config,
        "history": sanitized_history,
        "thread_id": thread_id,
        "run_id": run_id,
        "step": 0,
        "retry_count": 0,
        "max_retries": getattr(config, "verify_max_retries", 2),
        "state_schema_version": getattr(config, "state_schema_version", 1),
        "checkpoint_every": getattr(config, "checkpoint_every", 1),
        "state_scope": getattr(config, "state_scope", "thread"),
        "started_at": time.time(),
        "deadline_ts": time.time() + float(getattr(config, "max_execution_seconds", 120)),
    }
    run_service.start_run(
        run_id=run_id,
        thread_id=thread_id,
        mode=getattr(config, "mode", None),
        model_name=getattr(config, "model_name", None),
    )

    try:
        result = graph.invoke(state, config=config_payload)
        result["run_id"] = state.get("run_id")
        if "__interrupt__" not in result:
            run_service.finish_run(run_id=run_id, status=RunStatus.SUCCEEDED)
        return result
    except Exception as e:
        run_service.finish_run(run_id=run_id, status=RunStatus.FAILED, error=str(e))
        raise
