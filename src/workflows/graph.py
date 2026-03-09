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
    NoteWorker,
    MissionWorker,
)

if TYPE_CHECKING:
    from core.settings import AgentConfig


# =============================================================================
# Node Names (for graph definition)
# =============================================================================

NODE_SUPERVISOR = "supervisor"
NODE_PLANNING = "planning_worker"
NODE_RETRIEVAL = "retrieval_worker"
NODE_WEB_SEARCH = "web_search_worker"
NODE_SQL = "sql_worker"
NODE_MEMORY = "memory_worker"
NODE_NOTE = "note_worker"
NODE_MISSION = "mission_worker"
NODE_SYNTHESIZE = "synthesize"
NODE_HUMAN_CHECK = "human_check"
NODE_INPUT_GUARDRAIL = "input_guardrail"
NODE_OUTPUT_GUARDRAIL = "output_guardrail"
NODE_GUARDRAIL_REJECT = "guardrail_reject"


# =============================================================================
# Memory Extraction
# =============================================================================

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
        
        # Try to extract JSON array from response
        # Handle cases where LLM wraps it in markdown code blocks
        content = content.strip()
        if content.startswith("```"):
            # Remove markdown code blocks
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


# =============================================================================
# Node Functions
# =============================================================================

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

        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        with get_db_context() as db:
            ctx = EmotionalEngine.compute_emotional_context(db, uid, character_id)
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

        # Make routing decision (pass memories context + emotional context to supervisor)
        decision = supervisor.route(state, memories_context=memories_context, emotional_ctx=emotional_ctx)
        
        # Update state
        decisions = list(state.get("supervisor_decisions") or [])
        decisions.append(decision)
        
        iteration = (state.get("iteration_count") or 0) + 1
        
        updates = {
            "supervisor_decisions": decisions,
            "iteration_count": iteration,
            "current_worker": decision.next_worker,
        }
        
        # Set status based on action
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
        
        # Update timing
        timing = dict(state.get("timing") or {})
        timing[f"{result.worker_type.value}_ms"] = result.execution_time_ms
        
        return {
            "worker_results": worker_results,
            "gathered_context": context,
            "current_worker": None,
            "timing": timing,
        }
    
    return worker_node


def create_note_worker_node(config: Optional["AgentConfig"] = None):
    """
    Create the note worker node function.

    Unlike regular workers, the note worker does NOT append its output to
    ``gathered_context``.  Notes are a pure side-effect — the supervisor sees
    the worker ran (via worker_results) but note content is not fed back into
    the response synthesis, preventing the AI from regurgitating note content.
    """
    def note_worker_node(state: AgentState) -> Dict[str, Any]:
        worker = NoteWorker(config=config)
        log_info(f"=== {worker.name} Node (side-effect) ===")

        result = worker.execute(state)

        worker_results = list(state.get("worker_results") or [])
        worker_results.append(result)

        # Update timing but do NOT touch gathered_context
        timing = dict(state.get("timing") or {})
        timing[f"{result.worker_type.value}_ms"] = result.execution_time_ms

        return {
            "worker_results": worker_results,
            "current_worker": None,
            "timing": timing,
        }

    return note_worker_node


def create_sql_worker_node(config: Optional["AgentConfig"] = None):
    """
    Create the SQL worker node.
    
    SQL worker now uses LangGraph interrupt() for approval flow.
    """
    def sql_worker_node(state: AgentState) -> Dict[str, Any]:
        worker = SQLWorker(config=config)
        log_info(f"=== {worker.name} Node ===")
        
        # Execute the worker (may pause via interrupt() if approval needed)
        result = worker.execute(state)
        
        # Update state with result
        worker_results = list(state.get("worker_results") or [])
        worker_results.append(result)
        
        # Update gathered context
        context = state.get("gathered_context") or ""
        if result.success and result.content:
            new_context = f"\n\n=== {result.worker_type.value.upper()} ===\n{result.content}"
            context = context + new_context
        
        # Update timing
        timing = dict(state.get("timing") or {})
        timing[f"{result.worker_type.value}_ms"] = result.execution_time_ms
        
        return {
            "worker_results": worker_results,
            "gathered_context": context,
            "current_worker": None,
            "timing": timing,
        }
    
    return sql_worker_node


def create_synthesize_node(supervisor: SupervisorAgent, store: Optional[BaseStore] = None):
    """
    Create the synthesis node function.

    Synthesizes gathered context into a final response.
    If a store is provided, it extracts and saves important facts as memories.
    Also records the interaction with the emotional engine.
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

        # Generate final response (neutral synthesis — no character acting)
        raw_response = supervisor.generate_response(
            state, memories_context=memories_context, emotional_ctx=emotional_ctx,
        )

        # ── Persona Filter: rewrite neutral answer in character's voice ────
        metadata = state.get("metadata") or {}
        character_id = metadata.get("character")
        try:
            from workflows.persona_filter import PersonaFilter
            pf = PersonaFilter(character_id=character_id)
            response = pf.apply(raw_response, emotional_ctx=emotional_ctx)
        except Exception as e:
            log_warning(f"[PersonaFilter] Failed, using raw response: {e}")
            response = raw_response

        # Add response as AI message
        from langchain_core.messages import AIMessage
        messages = list(state.get("messages") or [])
        messages.append(AIMessage(content=response))
        
        # Store important facts as long-term memories (best-effort)
        if store:
            try:
                user_id = state.get("user_id")
                if user_id:
                    from workflows.memory_store import store_memory
                    from uuid import uuid4
                    
                    question = state.get("original_question", "")
                    gathered = state.get("gathered_context", "")
                    
                    if question and response and len(response) > 20:
                        # Phase 2: Extract key facts using LLM
                        metadata = state.get("metadata") or {}
                        facts = extract_key_facts(question, response, character_id=metadata.get("character"))
                        
                        if facts:
                            # Store each extracted fact as a semantic memory
                            for i, fact in enumerate(facts):
                                memory_key = f"fact_{uuid4().hex[:8]}"
                                store_memory(
                                    store,
                                    user_id=user_id,
                                    memory_key=memory_key,
                                    text=fact,
                                    memory_type="semantic",  # Facts are semantic memories
                                    metadata={
                                        "thread_id": state.get("thread_id"),
                                        "mode": state.get("mode"),
                                        "source": "fact_extraction",
                                    },
                                )
                            log_debug(f"Stored {len(facts)} facts for user {user_id}")
                        
                        # Also store the interaction as episodic memory (for context)
                        memory_key = f"interaction_{uuid4().hex[:8]}"
                        if gathered and len(gathered) > 100:
                            mode = state.get("mode", "chat")
                            summary = f"[{mode}] Q: {question[:200]} A: {response[:400]}"
                        else:
                            summary = f"Q: {question[:200]} A: {response[:400]}"
                        
                        store_memory(
                            store,
                            user_id=user_id,
                            memory_key=memory_key,
                            text=summary,
                            memory_type="episodic",
                            metadata={
                                "thread_id": state.get("thread_id"),
                                "mode": state.get("mode"),
                                "had_worker_context": bool(gathered and len(gathered) > 100),
                                "facts_extracted": len(facts),
                            },
                        )
                        log_debug(f"Stored episodic memory for user {user_id}: {memory_key}")
            except Exception as e:
                log_warning(f"Memory storage failed: {e}")

        # ── Emotional engine: record interaction + update state ────────
        emotional_update = None
        try:
            user_id = state.get("user_id")
            metadata = state.get("metadata") or {}
            character_id = metadata.get("character", "rio")

            if user_id:
                from uuid import UUID
                from infrastructure.database import get_db_context
                from services.emotional_engine import EmotionalEngine

                uid = UUID(user_id) if isinstance(user_id, str) else user_id
                question = state.get("original_question", "")

                # Analyze sentiment of the user's message
                sentiment = EmotionalEngine.analyze_sentiment(question)

                # Determine task success from worker results
                worker_results = state.get("worker_results") or []
                task_success = None
                if worker_results:
                    successes = sum(1 for r in worker_results if r.success)
                    failures = sum(1 for r in worker_results if not r.success)
                    if successes > 0 and failures == 0:
                        task_success = True
                    elif failures > 0 and successes == 0:
                        task_success = False

                with get_db_context() as db:
                    emo_state, mood_changed = EmotionalEngine.record_interaction(
                        db,
                        user_id=uid,
                        character_id=character_id,
                        sentiment=sentiment,
                        task_success=task_success,
                        context=question[:200],
                    )

                    tier = EmotionalEngine.get_relationship_tier(emo_state.affinity)
                    emotional_update = {
                        "mood": emo_state.mood.value,
                        "energy": round(emo_state.energy, 2),
                        "affinity": emo_state.affinity,
                        "relationship_tier": tier,
                        "mood_changed": mood_changed,
                        "streak_days": emo_state.streak_days,
                        "interaction_count": emo_state.interaction_count,
                    }
                    log_info(
                        f"[Emotion] Recorded interaction: mood={emo_state.mood.value} "
                        f"affinity={emo_state.affinity} tier={tier} changed={mood_changed}"
                    )
        except Exception as e:
            log_warning(f"[Emotion] Failed to record interaction: {e}")

        return {
            "messages": messages,
            "final_response": response,
            "status": ExecutionStatus.COMPLETED,
            "emotional_context": emotional_update,
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


# =============================================================================
# Routing Functions
# =============================================================================

def route_supervisor(state: AgentState) -> str:
    """
    Route from supervisor to next node based on decision.
    
    Returns the name of the next node to execute.
    """
    decisions = state.get("supervisor_decisions") or []
    
    if not decisions:
        log_warning("No supervisor decision found, going to synthesize")
        return NODE_SYNTHESIZE
    
    decision = decisions[-1]
    
    # Check for human interrupt
    if state.get("pending_human_interrupt"):
        return NODE_HUMAN_CHECK
    
    # Route based on action
    if decision.action == SupervisorAction.RESPOND:
        return NODE_SYNTHESIZE
    
    if decision.action == SupervisorAction.CLARIFY:
        return NODE_HUMAN_CHECK
    
    if decision.action == SupervisorAction.WAIT_HUMAN:
        return NODE_HUMAN_CHECK
    
    if decision.action == SupervisorAction.DELEGATE:
        worker = decision.next_worker
        if worker == WorkerType.PLANNING:
            return NODE_PLANNING
        if worker == WorkerType.RETRIEVAL:
            return NODE_RETRIEVAL
        if worker == WorkerType.WEB_SEARCH:
            return NODE_WEB_SEARCH
        if worker == WorkerType.SQL:
            return NODE_SQL
        if worker == WorkerType.MEMORY:
            return NODE_MEMORY
        if worker == WorkerType.NOTE:
            return NODE_NOTE
        if worker == WorkerType.MISSION:
            return NODE_MISSION
    
    # Default: synthesize
    return NODE_SYNTHESIZE


def route_after_worker(state: AgentState) -> str:
    """
    Route after worker completes - back to supervisor or end.
    """
    # Check iteration limit
    if has_exceeded_iterations(state):
        return NODE_SYNTHESIZE
    
    # Back to supervisor for next decision
    return NODE_SUPERVISOR


def route_after_sql_worker(state: AgentState) -> str:
    """
    Route after SQL worker completes.
    
    With interrupt(), the SQL worker handles approval internally,
    so we just need standard routing logic.
    """
    # Check iteration limit
    if has_exceeded_iterations(state):
        return NODE_SYNTHESIZE
    
    # Back to supervisor for next decision
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


# =============================================================================
# Graph Builder
# =============================================================================

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
    import os
    guardrails_enabled = os.getenv("GUARDRAILS_ENABLED", "true").lower() == "true"

    log_info("Building multi-agent workflow graph")
    if guardrails_enabled:
        log_info("Guardrails enabled")

    if store:
        log_info("Long-term memory store enabled")

    # Create agents
    supervisor = SupervisorAgent(config=config)

    # Create the graph
    graph = StateGraph(AgentState)

    # Add nodes (pass store to supervisor and synthesize for memory operations)
    graph.add_node(NODE_SUPERVISOR, create_supervisor_node(supervisor, store=store))
    graph.add_node(NODE_PLANNING, create_worker_node(PlanningWorker, config))
    graph.add_node(NODE_RETRIEVAL, create_worker_node(RetrievalWorker, config))
    graph.add_node(NODE_WEB_SEARCH, create_worker_node(WebSearchWorker, config))
    graph.add_node(NODE_SQL, create_sql_worker_node(config))
    graph.add_node(NODE_MEMORY, create_worker_node(MemoryWorker, config))
    graph.add_node(NODE_NOTE, create_note_worker_node(config))
    graph.add_node(NODE_MISSION, create_worker_node(MissionWorker, config))
    graph.add_node(NODE_SYNTHESIZE, create_synthesize_node(supervisor, store=store))
    graph.add_node(NODE_HUMAN_CHECK, human_check_node)

    # Conditionally add guardrail nodes
    if guardrails_enabled:
        from workflows.guardrails import (
            input_guardrail_node,
            route_after_input_guardrail,
            output_guardrail_node,
            route_after_output_guardrail,
            guardrail_reject_node,
        )
        graph.add_node(NODE_INPUT_GUARDRAIL, input_guardrail_node)
        graph.add_node(NODE_OUTPUT_GUARDRAIL, output_guardrail_node)
        graph.add_node(NODE_GUARDRAIL_REJECT, guardrail_reject_node)

        # START → input_guardrail (instead of supervisor)
        graph.add_edge(START, NODE_INPUT_GUARDRAIL)

        # input_guardrail → supervisor (pass) or → reject (fail)
        graph.add_conditional_edges(
            NODE_INPUT_GUARDRAIL,
            route_after_input_guardrail,
            {
                NODE_SUPERVISOR: NODE_SUPERVISOR,
                NODE_GUARDRAIL_REJECT: NODE_GUARDRAIL_REJECT,
            },
        )
    else:
        # No guardrails: START → supervisor directly
        graph.add_edge(START, NODE_SUPERVISOR)

    # Add conditional edges from supervisor
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
            NODE_SYNTHESIZE: NODE_SYNTHESIZE,
            NODE_HUMAN_CHECK: NODE_HUMAN_CHECK,
        },
    )

    # Add edges from workers back to supervisor
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

    # SQL worker uses standard routing (interrupt() handles approval internally)
    graph.add_conditional_edges(
        NODE_SQL,
        route_after_sql_worker,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, NODE_SYNTHESIZE: NODE_SYNTHESIZE},
    )

    # Synthesize → output_guardrail (if enabled) or → END
    if guardrails_enabled:
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

        # reject → END
        graph.add_edge(NODE_GUARDRAIL_REJECT, END)
    else:
        graph.add_edge(NODE_SYNTHESIZE, END)

    # Add edges from human check
    graph.add_conditional_edges(
        NODE_HUMAN_CHECK,
        route_human_check,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, END: END},
    )
    
    # Default interrupt points for human-in-the-loop
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


