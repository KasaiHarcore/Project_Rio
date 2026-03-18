"""
LangGraph Workflow Definition - Multi-agent Supervisor-Worker Architecture.

This module defines the LangGraph workflow that orchestrates the
supervisor-worker multi-agent system.

The graph structure:
    START
      │
      ▼
    ┌───────────┐
    │ Supervisor │◄────────────────┐
    │  (route)  │                  │
    └─────┬─────┘                  │
          │                        │
    ┌─────┴─────┐                  │
    │  Router   │                  │
    └─────┬─────┘                  │
          │                        │
    ┌─────┼─────┬─────┐            │
    │     │     │     │            │
    ▼     ▼     ▼     ▼            │
 [Plan] [RAG] [Web] [SQL]          │
    │     │     │  (HITL via       │
    │     │     │   interrupt())   │
    └─────┴─────┴─────┘            │
          │                        │
          └────────────────────────┘
          │
          ▼ (when ready)
    ┌───────────┐
    │ Synthesize│
    └─────┬─────┘
          │
          ▼
    ┌───────────┐
    │   Human   │ (if needed)
    │   Check   │
    └─────┬─────┘
          │
          ▼
        END
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, TYPE_CHECKING

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore

from utils.log import log_debug, log_error, log_info, log_success, log_warning
from workflows.state import (
    AgentState,
    ExecutionStatus,
    SupervisorAction,
    SupervisorDecision,
    WorkerResult,
    WorkerType,
    create_initial_state,
    get_gathered_context,
    has_exceeded_iterations,
    is_execution_complete,
    should_interrupt_for_human,
)
from workflows.supervisor import SupervisorAgent
from workflows.workers import (
    PlanningWorker,
    RetrievalWorker,
    SQLWorker,
    WebSearchWorker,
    MemoryWorker,
    OSControlWorker,
)
from workflows.workers.mission_graph import create_mission_node
from workflows.workers.note_graph import create_note_node

if TYPE_CHECKING:
    from core.settings import AgentConfig

NODE_SUPERVISOR = "supervisor"
NODE_PLANNING = "planning_worker"
NODE_RETRIEVAL = "retrieval_worker"
NODE_WEB_SEARCH = "web_search_worker"
NODE_SQL = "sql_worker"
NODE_MEMORY = "memory_worker"
NODE_NOTE = "note_worker"
NODE_MISSION = "mission_worker"
NODE_OS_CONTROL = "os_control_worker"
NODE_SYNTHESIZE = "synthesize"
NODE_HUMAN_CHECK = "human_check"
NODE_INPUT_GUARDRAIL = "input_guardrail"
NODE_OUTPUT_GUARDRAIL = "output_guardrail"
NODE_GUARDRAIL_REJECT = "guardrail_reject"


# ═══════════════════════════════════════════════════════════════════════════
# Internal Knowledge Auto-Context Fetchers
# ═══════════════════════════════════════════════════════════════════════════

def _fetch_note_hints(state: AgentState) -> str:
    """Quick semantic search across the user's notes.

    Returns a short summary string suitable for injecting into the
    supervisor / synthesize prompt so the LLM is *aware* that relevant
    notes exist.  The full note content is NOT returned — the supervisor
    decides whether to delegate to the NOTE worker for detail.

    Best-effort: returns "" on any error.
    """
    user_id = state.get("user_id")
    question = state.get("original_question", "")
    if not user_id or not question or len(question) < 5:
        return ""

    try:
        import json
        from infrastructure.database.session import SessionLocal
        from infrastructure.tools.note_knowledge_tool import NoteKnowledgeTool

        db = SessionLocal()
        try:
            tool = NoteKnowledgeTool(db)
            raw = tool.search_notes(query=question, user_id=str(user_id), k=5)
            results = json.loads(raw) if raw else []
            if not results:
                return ""

            # Also fetch collections for context
            col_raw = tool.list_collections(str(user_id))
            collections = json.loads(col_raw) if col_raw else []
            col_map = {c["id"]: c["name"] for c in collections}

            lines = ["## Sensei's Relevant Notes (auto-fetched from knowledge base)"]
            for i, note in enumerate(results[:5], 1):
                title = note.get("title", "Untitled")
                preview = (note.get("content") or "")[:150]
                source = note.get("source", "user")
                col_ids = note.get("collection_ids") or []
                col_names = [col_map[cid] for cid in col_ids if cid in col_map]
                col_str = f" [{', '.join(col_names)}]" if col_names else ""
                lines.append(
                    f"{i}. **{title}**{col_str} ({source}) — {preview}..."
                )

            lines.append(
                "\n*If these notes are relevant, consider delegating to NOTE worker "
                "for full detail before using external sources.*"
            )
            hint = "\n".join(lines)
            log_debug(f"Note hints: {len(results)} relevant note(s) found")
            return hint
        finally:
            db.close()
    except Exception as e:
        log_debug(f"Note hint fetch failed (non-fatal): {e}")
        return ""


def _fetch_mission_hints(state: AgentState) -> str:
    """Quick check for the user's active missions related to the question.

    Returns a short summary of active/draft missions so the supervisor
    can connect the question to ongoing tasks.

    Best-effort: returns "" on any error.
    """
    user_id = state.get("user_id")
    question = state.get("original_question", "")
    if not user_id or not question or len(question) < 5:
        return ""

    try:
        from infrastructure.tools.mission_tool import MissionTool

        tool = MissionTool()
        missions = tool.list_active_missions(str(user_id), limit=10)
        if not missions:
            return ""

        # Simple keyword overlap to filter relevant missions
        q_words = set(question.lower().split())
        relevant = []
        for m in missions:
            title = (m.get("title") or "").lower()
            desc = (m.get("description") or "").lower()
            category = (m.get("category") or "").lower()
            combined = f"{title} {desc} {category}"
            overlap = sum(1 for w in q_words if len(w) > 3 and w in combined)
            if overlap > 0:
                relevant.append((overlap, m))

        if not relevant:
            return ""

        relevant.sort(key=lambda x: x[0], reverse=True)
        top = [m for _, m in relevant[:3]]

        lines = ["## Sensei's Related Missions (auto-fetched)"]
        for m in top:
            title = m.get("title", "Untitled")
            status = m.get("status", "active")
            progress = m.get("progress", 0)
            steps_done = m.get("steps_completed", 0)
            steps_total = m.get("steps_total", 0)
            category = m.get("category", "")
            cat_str = f" [{category}]" if category else ""
            lines.append(
                f"- **{title}**{cat_str} — {status}, "
                f"{progress}% complete ({steps_done}/{steps_total} steps)"
            )

        lines.append(
            "\n*Sensei may be working on these tasks. Consider the connection "
            "when answering.*"
        )
        hint = "\n".join(lines)
        log_debug(f"Mission hints: {len(top)} relevant mission(s) found")
        return hint
    except Exception as e:
        log_debug(f"Mission hint fetch failed (non-fatal): {e}")
        return ""


FACT_EXTRACTION_PROMPT = """Extract key facts from this conversation that would be useful to remember about Sensei for future conversations.

Focus on:
- Sensei's preferences (e.g., "prefers Python", "likes concise answers")
- Personal information shared (e.g., "works at Google", "name is John")
- Important decisions or conclusions
- Specific interests or goals mentioned
- Technical context (e.g., "working on a React project")

Conversation:
Sensei: {question}
Assistant: {response}

Return ONLY a JSON array of fact strings. If no memorable facts, return empty array [].
Example: ["Sensei prefers Python over JavaScript", "Sensei is building a chat application"]

Facts:"""


def extract_key_facts(question: str, response: str, character_id: str | None = None) -> List[str]:
    """
    Use LLM to extract key memorable facts from a conversation.
    
    Returns a list of fact strings suitable for long-term memory storage.
    """
    from infrastructure.llm import form
    
    if not question or not response:
        return []
    
    # Skip trivial exchanges
    if len(question) < 10 or len(response) < 30:
        return []
    
    try:
        if not form.SELECTED_MODEL:
            return []
        
        if not form.SELECTED_MODEL.llm:
            form.SELECTED_MODEL.setup()
        
        prompt = FACT_EXTRACTION_PROMPT.format(
            question=question[:500],
            response=response[:1000],
        )
        
        result = form.SELECTED_MODEL.llm.invoke(prompt)
        content = getattr(result, "content", str(result))
        
        # Parse JSON array from response
        import json
        import re
        
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"```(?:json)?\s*", "", content)
            content = content.replace("```", "").strip()
        
        # Find the JSON array
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            facts = json.loads(match.group())
            if isinstance(facts, list):
                # Filter and clean facts
                return [str(f).strip() for f in facts if f and len(str(f).strip()) > 5][:5]
        
        return []
        
    except Exception as e:
        log_debug(f"Fact extraction failed: {e}")
        return []


def _fetch_emotional_context(state: AgentState) -> Optional[Dict[str, str]]:
    """Fetch emotional context for the current user/character pair.

    Returns None if user_id is missing or on any error (best-effort).
    """
    user_id = state.get("user_id")
    metadata = state.get("metadata") or {}
    character_id = metadata.get("character", "rio")

    if not user_id:
        return None

    try:
        from uuid import UUID
        from infrastructure.database import get_db_context
        from services.emotional_engine import EmotionalEngine
        from repositories.emotional_state_repository import EmotionalStateRepository

        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        with get_db_context() as db:
            engine = EmotionalEngine(EmotionalStateRepository(db))
            ctx = engine.compute_emotional_context(uid, character_id)
            log_debug(
                f"[Emotion] Fetched context: mood={ctx.get('current_mood')}, "
                f"tier={ctx.get('relationship_tier')}, energy={ctx.get('energy_level')}"
            )
            return ctx
    except Exception as e:
        log_warning(f"[Emotion] Failed to fetch emotional context: {e}")
        return None


def create_supervisor_node(supervisor: SupervisorAgent, store: Optional[BaseStore] = None):
    """
    Create the supervisor node function.

    The supervisor analyzes the state and makes routing decisions.
    If a store is provided, it retrieves relevant long-term memories.
    """
    def supervisor_node(state: AgentState, *, store: Optional[BaseStore] = store) -> Dict[str, Any]:
        log_info("=== Supervisor Node ===")

        # Retrieve long-term memories if store is available
        memories_context = ""
        if store:
            try:
                user_id = state.get("user_id")
                question = state.get("original_question", "")
                if user_id and question:
                    from workflows.memory_store import (
                        search_memories,
                        format_memories_for_prompt,
                    )
                    memories = search_memories(
                        store,
                        user_id=user_id,
                        query=question,
                        limit=5,
                    )
                    memories_context = format_memories_for_prompt(memories)
                    if memories_context:
                        log_debug(f"Retrieved {len(memories)} relevant memories")
            except Exception as e:
                log_warning(f"Memory retrieval failed: {e}")

        # Fetch emotional context for persona-aware routing
        emotional_ctx = _fetch_emotional_context(state)

        # Fetch internal knowledge hints (notes + missions)
        notes_hint = _fetch_note_hints(state)
        missions_hint = _fetch_mission_hints(state)

        decision = supervisor.route(
            state,
            memories_context=memories_context,
            emotional_ctx=emotional_ctx,
            notes_hint=notes_hint,
            missions_hint=missions_hint,
        )
        
        decisions = list(state.get("supervisor_decisions") or [])
        decisions.append(decision)
        
        iteration = (state.get("iteration_count") or 0) + 1
        
        updates = {
            "supervisor_decisions": decisions,
            "iteration_count": iteration,
            "current_worker": decision.next_worker,
        }
        
        if decision.action == SupervisorAction.RESPOND:
            updates["status"] = ExecutionStatus.RUNNING
        elif decision.action == SupervisorAction.CLARIFY:
            updates["status"] = ExecutionStatus.WAITING_HUMAN
            updates["pending_human_interrupt"] = supervisor.request_clarification(state)
        elif decision.action == SupervisorAction.WAIT_HUMAN:
            updates["status"] = ExecutionStatus.WAITING_HUMAN
        else:
            updates["status"] = ExecutionStatus.RUNNING
        
        return updates
    
    return supervisor_node


def _build_completed_action(result: WorkerResult) -> Dict[str, Any]:
    """Build a structured completed-action entry from a WorkerResult.

    The *fingerprint* uniquely identifies (worker, action, outcome) and is
    used by route_after_worker to detect loops without any hard-coded rules.
    """
    action = (result.metadata or {}).get("action", "")
    fingerprint = f"{result.worker_type.value}:{action}:{result.success}"
    # Short human-readable summary for supervisor context injection
    if result.success and result.content:
        summary = result.content[:120].replace("\n", " ")
    elif result.error:
        summary = result.error[:120]
    else:
        summary = "no output"
    return {
        "worker": result.worker_type.value,
        "action": action,
        "success": result.success,
        "fingerprint": fingerprint,
        "summary": summary,
    }


def create_worker_node(worker_class, config: Optional["AgentConfig"] = None):
    """
    Create a worker node function.

    Workers execute their specialized task and return results.
    """
    def worker_node(state: AgentState) -> Dict[str, Any]:
        worker = worker_class(config=config)
        log_info(f"=== {worker.name} Node ===")

        # Execute the worker
        result = worker.execute(state)

        # Update state with result
        worker_results = list(state.get("worker_results") or [])
        worker_results.append(result)

        # Update gathered context
        context = state.get("gathered_context") or ""
        if result.success and result.content:
            new_context = f"\n\n=== {result.worker_type.value.upper()} ===\n{result.content}"
            context = context + new_context

        timing = dict(state.get("timing") or {})
        timing[f"{result.worker_type.value}_ms"] = result.execution_time_ms

        # Append structured completed-action record
        completed = list(state.get("completed_actions") or [])
        completed.append(_build_completed_action(result))

        return {
            "worker_results": worker_results,
            "gathered_context": context,
            "current_worker": None,
            "timing": timing,
            "completed_actions": completed,
        }

    return worker_node


def create_sql_worker_node(config: Optional["AgentConfig"] = None):
    """
    Create the SQL worker node.

    SQL worker now uses LangGraph interrupt() for approval flow.
    """
    def sql_worker_node(state: AgentState) -> Dict[str, Any]:
        worker = SQLWorker(config=config)
        log_info(f"=== {worker.name} Node ===")

        result = worker.execute(state)

        worker_results = list(state.get("worker_results") or [])
        worker_results.append(result)

        context = state.get("gathered_context") or ""
        if result.success and result.content:
            new_context = f"\n\n=== {result.worker_type.value.upper()} ===\n{result.content}"
            context = context + new_context

        timing = dict(state.get("timing") or {})
        timing[f"{result.worker_type.value}_ms"] = result.execution_time_ms

        completed = list(state.get("completed_actions") or [])
        completed.append(_build_completed_action(result))

        return {
            "worker_results": worker_results,
            "gathered_context": context,
            "current_worker": None,
            "timing": timing,
            "completed_actions": completed,
        }

    return sql_worker_node


def _run_post_response_tasks(
    state_snapshot: Dict[str, Any],
    response: str,
    store: Optional[BaseStore],
) -> None:
    """Fire-and-forget: fact extraction, memory storage, and emotional engine.

    Runs in a background thread so the user gets the response immediately.
    """
    user_id = state_snapshot.get("user_id")
    question = state_snapshot.get("original_question", "")
    metadata = state_snapshot.get("metadata") or {}
    character_id = metadata.get("character", "rio")

    # ── Memory storage (fact extraction + episodic) ───────────────────
    # NOTE: We open our own store connection here because this runs in a
    # background thread — the caller's context-managed store may already
    # be closed by the time we execute.
    if store and user_id and question and response and len(response) > 20:
        try:
            from workflows.memory_store import store_memory, memory_store_context
            from uuid import uuid4

            gathered = state_snapshot.get("gathered_context", "")

            facts = extract_key_facts(question, response, character_id=character_id)

            with memory_store_context() as bg_store:
                if facts:
                    for fact in facts:
                        store_memory(
                            bg_store,
                            user_id=user_id,
                            memory_key=f"fact_{uuid4().hex[:8]}",
                            text=fact,
                            memory_type="semantic",
                            metadata={
                                "thread_id": state_snapshot.get("thread_id"),
                                "mode": state_snapshot.get("mode"),
                                "source": "fact_extraction",
                            },
                        )
                    log_debug(f"Stored {len(facts)} facts for user {user_id}")

                memory_key = f"interaction_{uuid4().hex[:8]}"
                if gathered and len(gathered) > 100:
                    mode = state_snapshot.get("mode", "chat")
                    summary = f"[{mode}] Q: {question[:200]} A: {response[:400]}"
                else:
                    summary = f"Q: {question[:200]} A: {response[:400]}"

                store_memory(
                    bg_store,
                    user_id=user_id,
                    memory_key=memory_key,
                    text=summary,
                    memory_type="episodic",
                    metadata={
                        "thread_id": state_snapshot.get("thread_id"),
                        "mode": state_snapshot.get("mode"),
                        "had_worker_context": bool(gathered and len(gathered) > 100),
                        "facts_extracted": len(facts) if facts else 0,
                    },
                )
        except Exception as e:
            log_warning(f"Memory storage failed: {e}")

    # ── Emotional engine ─────────────────────────────────────────────
    if user_id:
        try:
            from uuid import UUID
            from infrastructure.database import get_db_context
            from services.emotional_engine import EmotionalEngine
            from repositories.emotional_state_repository import EmotionalStateRepository

            uid = UUID(user_id) if isinstance(user_id, str) else user_id

            with get_db_context() as db:
                engine = EmotionalEngine(EmotionalStateRepository(db))
                sentiment = engine.analyze_sentiment(question)

                worker_results = state_snapshot.get("worker_results") or []
                task_success = None
                if worker_results:
                    successes = sum(1 for r in worker_results if r.get("success", False))
                    failures = sum(1 for r in worker_results if not r.get("success", True))
                    if successes > 0 and failures == 0:
                        task_success = True
                    elif failures > 0 and successes == 0:
                        task_success = False

                engine.record_interaction(
                    user_id=uid,
                    character_id=character_id,
                    sentiment=sentiment,
                    task_success=task_success,
                    context=question[:200],
                )
        except Exception as e:
            log_warning(f"[Emotion] Background task failed: {e}")


def create_synthesize_node(supervisor: SupervisorAgent, store: Optional[BaseStore] = None):
    """
    Create the synthesis node function.

    Synthesizes gathered context into a final response.
    Memory storage and emotional updates run in a background thread
    so they don't block the response from reaching the user.
    """
    def synthesize_node(state: AgentState, *, store: Optional[BaseStore] = store) -> Dict[str, Any]:
        log_info("=== Synthesize Node ===")

        # Retrieve long-term memories from PostgresStore for response generation
        memories_context = ""
        if store:
            try:
                user_id = state.get("user_id")
                question = state.get("original_question", "")
                if user_id and question:
                    from workflows.memory_store import (
                        search_memories,
                        format_memories_for_prompt,
                    )
                    memories = search_memories(
                        store,
                        user_id=user_id,
                        query=question,
                        limit=5,
                    )
                    memories_context = format_memories_for_prompt(memories)
                    if memories_context:
                        log_debug(f"Synthesize: retrieved {len(memories)} long-term memories")
            except Exception as e:
                log_warning(f"Synthesize memory retrieval failed: {e}")

        # Fetch emotional context for persona-aware response generation
        emotional_ctx = _fetch_emotional_context(state)

        # Fetch internal knowledge hints for response enrichment
        notes_hint = _fetch_note_hints(state)
        missions_hint = _fetch_mission_hints(state)

        # Generate final response directly in character's voice (single LLM call)
        metadata = state.get("metadata") or {}
        character_id = metadata.get("character")
        response = supervisor.generate_response(
            state,
            memories_context=memories_context,
            emotional_ctx=emotional_ctx,
            character_id=character_id,
            notes_hint=notes_hint,
            missions_hint=missions_hint,
        )

        from langchain_core.messages import AIMessage
        messages = list(state.get("messages") or [])
        messages.append(AIMessage(content=response))

        # ── Fire-and-forget: memory + emotional engine in background ────
        import threading

        # Snapshot only serializable state fields needed by the background task
        state_snapshot = {
            "user_id": state.get("user_id"),
            "original_question": state.get("original_question", ""),
            "gathered_context": state.get("gathered_context", ""),
            "metadata": metadata,
            "thread_id": state.get("thread_id"),
            "mode": state.get("mode"),
            "worker_results": [
                {"success": getattr(r, "success", True)}
                for r in (state.get("worker_results") or [])
            ],
        }
        threading.Thread(
            target=_run_post_response_tasks,
            args=(state_snapshot, response, store),
            daemon=True,
        ).start()

        return {
            "messages": messages,
            "final_response": response,
            "status": ExecutionStatus.COMPLETED,
        }

    return synthesize_node


def human_check_node(state: AgentState) -> Dict[str, Any]:
    """
    Human-in-the-loop check node.
    
    This node handles human interruptions and approvals.
    """
    log_info("=== Human Check Node ===")
    
    # Check if there's a pending interrupt
    interrupt = state.get("pending_human_interrupt")
    
    if interrupt and interrupt.required:
        # Still waiting for human input
        return {"status": ExecutionStatus.WAITING_HUMAN}
    
    # Human input received or not needed
    return {"status": ExecutionStatus.RUNNING}


# ── Declarative routing tables ────────────────────────────────────────────
# Adding a new supervisor action or worker only requires a new entry here;
# the routing function itself never needs to change.

_ACTION_NODE_MAP: Dict[str, str] = {
    SupervisorAction.RESPOND.value:     NODE_SYNTHESIZE,
    SupervisorAction.CLARIFY.value:     NODE_HUMAN_CHECK,
    SupervisorAction.WAIT_HUMAN.value:  NODE_HUMAN_CHECK,
}

_WORKER_NODE_MAP: Dict[str, str] = {
    WorkerType.PLANNING.value:    NODE_PLANNING,
    WorkerType.RETRIEVAL.value:   NODE_RETRIEVAL,
    WorkerType.WEB_SEARCH.value:  NODE_WEB_SEARCH,
    WorkerType.SQL.value:         NODE_SQL,
    WorkerType.MEMORY.value:      NODE_MEMORY,
    WorkerType.NOTE.value:        NODE_NOTE,
    WorkerType.MISSION.value:     NODE_MISSION,
    WorkerType.OS_CONTROL.value:  NODE_OS_CONTROL,
}


def route_supervisor(state: AgentState) -> str:
    """Route from supervisor decision to the next graph node.

    Uses declarative lookup tables so adding a new worker or action
    only requires a registry entry — no code changes here.
    """
    decisions = state.get("supervisor_decisions") or []
    if not decisions:
        log_warning("No supervisor decision found, going to synthesize")
        return NODE_SYNTHESIZE

    decision = decisions[-1]

    if state.get("pending_human_interrupt"):
        return NODE_HUMAN_CHECK

    if decision.action == SupervisorAction.DELEGATE:
        worker = decision.next_worker
        node = _WORKER_NODE_MAP.get(worker.value if worker else "") if worker else None
        if node:
            return node
        log_warning(f"Unknown worker type '{worker}' — falling through to synthesize")
        return NODE_SYNTHESIZE

    return _ACTION_NODE_MAP.get(decision.action.value, NODE_SYNTHESIZE)


def _detect_loop(state: AgentState) -> bool:
    """Return True if the workflow is spinning on the same action.

    A loop is defined as: the most-recently completed action's fingerprint
    already appeared in an earlier completed action *within the same turn*.
    This is purely data-driven — no worker names or action strings are
    hard-coded here.  Any (worker, action, success) triple that repeats
    is treated as a loop regardless of which worker caused it.
    """
    completed = state.get("completed_actions") or []
    if len(completed) < 2:
        return False
    last_fp = completed[-1]["fingerprint"]
    earlier_fps = {c["fingerprint"] for c in completed[:-1]}
    if last_fp in earlier_fps:
        log_warning(
            f"Loop detected: action '{last_fp}' already completed this turn "
            "— routing to synthesize"
        )
        return True
    return False


def route_after_worker(state: AgentState) -> str:
    """Route after a worker completes — back to supervisor or straight to synthesize."""
    if has_exceeded_iterations(state):
        return NODE_SYNTHESIZE

    if _detect_loop(state):
        return NODE_SYNTHESIZE

    return NODE_SUPERVISOR


def route_after_sql_worker(state: AgentState) -> str:
    """Route after the SQL worker completes."""
    if has_exceeded_iterations(state):
        return NODE_SYNTHESIZE

    if _detect_loop(state):
        return NODE_SYNTHESIZE

    return NODE_SUPERVISOR


def route_human_check(state: AgentState) -> str:
    """
    Route after human check.
    """
    status = state.get("status")
    
    if status == ExecutionStatus.WAITING_HUMAN:
        # Still waiting, stay at human check (graph will interrupt)
        return END
    
    # Human responded, continue
    return NODE_SUPERVISOR


def build_workflow_graph(
    config: Optional["AgentConfig"] = None,
    checkpointer: Any = None,
    store: Optional[BaseStore] = None,
    interrupt_before: Optional[List[str]] = None,
    interrupt_after: Optional[List[str]] = None,
) -> CompiledStateGraph:
    """
    Build the multi-agent workflow graph.
    
    Args:
        config: Agent configuration
        checkpointer: Optional checkpointer for state persistence (short-term memory)
        store: Optional PostgresStore for long-term memory with semantic search
        interrupt_before: Nodes to interrupt before (human-in-the-loop)
        interrupt_after: Nodes to interrupt after
    
    Returns:
        Compiled LangGraph workflow
    """
    input_guardrail_enabled = config.enable_input_guardrail if config else False
    output_guardrail_enabled = config.enable_output_guardrail if config else False

    log_info("Building multi-agent workflow graph")
    if input_guardrail_enabled:
        log_info("Input guardrail enabled")
    if output_guardrail_enabled:
        log_info("Output guardrail enabled")

    if store:
        log_info("Long-term memory store enabled")

    supervisor = SupervisorAgent(config=config)

    graph = StateGraph(AgentState)

    graph.add_node(NODE_SUPERVISOR, create_supervisor_node(supervisor, store=store))
    graph.add_node(NODE_PLANNING, create_worker_node(PlanningWorker, config))
    graph.add_node(NODE_RETRIEVAL, create_worker_node(RetrievalWorker, config))
    graph.add_node(NODE_WEB_SEARCH, create_worker_node(WebSearchWorker, config))
    graph.add_node(NODE_SQL, create_sql_worker_node(config))
    graph.add_node(NODE_MEMORY, create_worker_node(MemoryWorker, config))
    graph.add_node(NODE_NOTE, create_note_node(config))
    graph.add_node(NODE_MISSION, create_mission_node(config))
    graph.add_node(NODE_OS_CONTROL, create_worker_node(OSControlWorker, config))
    graph.add_node(NODE_SYNTHESIZE, create_synthesize_node(supervisor, store=store))
    graph.add_node(NODE_HUMAN_CHECK, human_check_node)

    # Conditionally add guardrail nodes
    any_guardrail = input_guardrail_enabled or output_guardrail_enabled
    if any_guardrail:
        from workflows.guardrails import guardrail_reject_node
        graph.add_node(NODE_GUARDRAIL_REJECT, guardrail_reject_node)

    if input_guardrail_enabled:
        from workflows.guardrails import (
            input_guardrail_node,
            route_after_input_guardrail,
        )
        graph.add_node(NODE_INPUT_GUARDRAIL, input_guardrail_node)

        # START → input_guardrail → supervisor (pass) or → reject (fail)
        graph.add_edge(START, NODE_INPUT_GUARDRAIL)
        graph.add_conditional_edges(
            NODE_INPUT_GUARDRAIL,
            route_after_input_guardrail,
            {
                NODE_SUPERVISOR: NODE_SUPERVISOR,
                NODE_GUARDRAIL_REJECT: NODE_GUARDRAIL_REJECT,
            },
        )
    else:
        # No input guardrail: START → supervisor directly
        graph.add_edge(START, NODE_SUPERVISOR)

    graph.add_conditional_edges(
        NODE_SUPERVISOR,
        route_supervisor,
        {
            NODE_PLANNING: NODE_PLANNING,
            NODE_RETRIEVAL: NODE_RETRIEVAL,
            NODE_WEB_SEARCH: NODE_WEB_SEARCH,
            NODE_SQL: NODE_SQL,
            NODE_MEMORY: NODE_MEMORY,
            NODE_NOTE: NODE_NOTE,
            NODE_MISSION: NODE_MISSION,
            NODE_OS_CONTROL: NODE_OS_CONTROL,
            NODE_SYNTHESIZE: NODE_SYNTHESIZE,
            NODE_HUMAN_CHECK: NODE_HUMAN_CHECK,
        },
    )

    graph.add_conditional_edges(
        NODE_PLANNING,
        route_after_worker,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, NODE_SYNTHESIZE: NODE_SYNTHESIZE},
    )
    graph.add_conditional_edges(
        NODE_RETRIEVAL,
        route_after_worker,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, NODE_SYNTHESIZE: NODE_SYNTHESIZE},
    )
    graph.add_conditional_edges(
        NODE_WEB_SEARCH,
        route_after_worker,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, NODE_SYNTHESIZE: NODE_SYNTHESIZE},
    )
    graph.add_conditional_edges(
        NODE_MEMORY,
        route_after_worker,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, NODE_SYNTHESIZE: NODE_SYNTHESIZE},
    )
    graph.add_conditional_edges(
        NODE_NOTE,
        route_after_worker,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, NODE_SYNTHESIZE: NODE_SYNTHESIZE},
    )
    graph.add_conditional_edges(
        NODE_MISSION,
        route_after_worker,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, NODE_SYNTHESIZE: NODE_SYNTHESIZE},
    )
    graph.add_conditional_edges(
        NODE_OS_CONTROL,
        route_after_worker,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, NODE_SYNTHESIZE: NODE_SYNTHESIZE},
    )

    # SQL worker uses standard routing (interrupt() handles approval internally)
    graph.add_conditional_edges(
        NODE_SQL,
        route_after_sql_worker,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, NODE_SYNTHESIZE: NODE_SYNTHESIZE},
    )

    # Synthesize → output_guardrail (if enabled) or → END
    if output_guardrail_enabled:
        from workflows.guardrails import (
            output_guardrail_node,
            route_after_output_guardrail,
        )
        graph.add_node(NODE_OUTPUT_GUARDRAIL, output_guardrail_node)
        graph.add_edge(NODE_SYNTHESIZE, NODE_OUTPUT_GUARDRAIL)

        # output_guardrail → END (pass) or → reject (fail)
        graph.add_conditional_edges(
            NODE_OUTPUT_GUARDRAIL,
            route_after_output_guardrail,
            {
                END: END,
                NODE_GUARDRAIL_REJECT: NODE_GUARDRAIL_REJECT,
            },
        )
    else:
        graph.add_edge(NODE_SYNTHESIZE, END)

    # reject → END (if any guardrail is active)
    if any_guardrail:
        graph.add_edge(NODE_GUARDRAIL_REJECT, END)

    graph.add_conditional_edges(
        NODE_HUMAN_CHECK,
        route_human_check,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, END: END},
    )
    
    default_interrupt_before = interrupt_before or []
    default_interrupt_after = interrupt_after or []
    
    # Always allow interrupt at human check
    if NODE_HUMAN_CHECK not in default_interrupt_before:
        default_interrupt_before.append(NODE_HUMAN_CHECK)
    
    # Compile the graph with checkpointer (short-term) and store (long-term)
    compiled = graph.compile(
        checkpointer=checkpointer,
        store=store,
        interrupt_before=default_interrupt_before if default_interrupt_before else None,
        interrupt_after=default_interrupt_after if default_interrupt_after else None,
    )
    
    log_success("Workflow graph compiled successfully")
    if store:
        log_success("Long-term memory enabled with semantic search")
    return compiled


