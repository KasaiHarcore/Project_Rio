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

from backend.utils.log import log_debug, log_error, log_info, log_success, log_warning
from backend.application.workflows.state import (
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
from backend.application.workflows.supervisor import SupervisorAgent
from backend.application.workflows.workers import (
    PlanningWorker,
    RetrievalWorker,
    SQLWorker,
    WebSearchWorker,
    MemoryWorker,
)

if TYPE_CHECKING:
    from backend.core.settings import AgentConfig


# =============================================================================
# Node Names (for graph definition)
# =============================================================================

NODE_SUPERVISOR = "supervisor"
NODE_PLANNING = "planning_worker"
NODE_RETRIEVAL = "retrieval_worker"
NODE_WEB_SEARCH = "web_search_worker"
NODE_SQL = "sql_worker"
NODE_MEMORY = "memory_worker"
NODE_SYNTHESIZE = "synthesize"
NODE_HUMAN_CHECK = "human_check"


# =============================================================================
# Memory Extraction
# =============================================================================

FACT_EXTRACTION_PROMPT = """Extract key facts from this conversation that would be useful to remember about the user for future conversations.

Focus on:
- User preferences (e.g., "prefers Python", "likes concise answers")
- Personal information shared (e.g., "works at Google", "name is John")
- Important decisions or conclusions
- Specific interests or goals mentioned
- Technical context (e.g., "working on a React project")

Conversation:
User: {question}
Assistant: {response}

Return ONLY a JSON array of fact strings. If no memorable facts, return empty array [].
Example: ["User prefers Python over JavaScript", "User is building a chat application"]

Facts:"""


def extract_key_facts(question: str, response: str) -> List[str]:
    """
    Use LLM to extract key memorable facts from a conversation.
    
    Returns a list of fact strings suitable for long-term memory storage.
    """
    from backend.infrastructure.integrations.llm import form
    
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
                    from backend.application.workflows.memory_store import (
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
        
        # Make routing decision (pass memories context to supervisor)
        decision = supervisor.route(state, memories_context=memories_context)
        
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
    """
    def synthesize_node(state: AgentState, *, store: Optional[BaseStore] = store) -> Dict[str, Any]:
        log_info("=== Synthesize Node ===")
        
        # Generate final response
        response = supervisor.generate_response(state)
        
        # Add response as AI message
        from langchain_core.messages import AIMessage
        messages = list(state.get("messages") or [])
        messages.append(AIMessage(content=response))
        
        # Store important facts as long-term memories (best-effort)
        if store:
            try:
                user_id = state.get("user_id")
                if user_id:
                    from backend.application.workflows.memory_store import store_memory
                    from uuid import uuid4
                    
                    question = state.get("original_question", "")
                    gathered = state.get("gathered_context", "")
                    
                    if question and response and len(response) > 20:
                        # Phase 2: Extract key facts using LLM
                        facts = extract_key_facts(question, response)
                        
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


def sql_approval_node(state: AgentState) -> Dict[str, Any]:
    """
    SQL Approval node for Human-in-the-Loop SQL operations.
    
    This node pauses execution and waits for user approval
    of dangerous SQL operations (WRITE, DELETE, etc.).
    
    Flow:
    1. Check if there's a pending SQL approval request
    2. If yes, create a HumanInterrupt and wait
    3. When resumed, the SQL worker will process the response
    """
    log_info("=== SQL Approval Node ===")
    
    pending_approval = state.get("pending_sql_approval")
    
    if not pending_approval:
        log_warning("SQL Approval node called without pending approval")
        return {"status": ExecutionStatus.RUNNING}
    
    # Create human interrupt for SQL approval
    from backend.application.workflows.state import HumanInterrupt, HumanInterruptType
    
    request = pending_approval.get("request", {})
    
    interrupt = HumanInterrupt(
        interrupt_type=HumanInterruptType.APPROVAL,
        message=request.get("explanation", "SQL operation requires approval"),
        options=["approve", "modify", "reject"],
        context={
            "type": "sql_approval",
            "request_id": request.get("request_id"),
            "generated_sql": request.get("generated_sql"),
            "operation_type": request.get("operation_type"),
            "danger_level": request.get("danger_level"),
            "affected_tables": request.get("affected_tables", []),
            "warnings": request.get("warnings", []),
        },
        required=True,
    )
    
    log_info(f"SQL approval interrupt created: {request.get('request_id')}")
    
    return {
        "pending_human_interrupt": interrupt,
        "status": ExecutionStatus.WAITING_HUMAN,
    }


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
    log_info("Building multi-agent workflow graph")
    
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
    graph.add_node(NODE_SYNTHESIZE, create_synthesize_node(supervisor, store=store))
    graph.add_node(NODE_HUMAN_CHECK, human_check_node)
    
    # Add edges from START
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
    
    # SQL worker uses standard routing (interrupt() handles approval internally)
    graph.add_conditional_edges(
        NODE_SQL,
        route_after_sql_worker,
        {NODE_SUPERVISOR: NODE_SUPERVISOR, NODE_SYNTHESIZE: NODE_SYNTHESIZE},
    )
    
    # Add edges from synthesize to END
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


def get_graph_visualization() -> str:
    """
    Get a text-based visualization of the graph structure.
    
    Returns:
        ASCII art representation of the graph
    """
    return """
    Multi-Agent Supervisor-Worker Workflow
    =====================================
    
                    START
                      │
                      ▼
                ┌───────────┐
                │ Supervisor │◄────────────────┐
                │  (route)   │                 │
                └─────┬─────┘                  │
                      │                        │
          ┌───────────┼───────────┐            │
          │           │           │            │
          ▼           ▼           ▼            │
    ┌──────────┐ ┌──────────┐ ┌──────────┐    │
    │ Planning │ │ Retrieval│ │Web Search│    │
    │  Worker  │ │  Worker  │ │  Worker  │    │
    └────┬─────┘ └────┬─────┘ └────┬─────┘    │
          │           │           │            │
          └───────────┼───────────┘            │
                      │           ┌──────────┐ │
                      │           │   SQL    │ │
                      │           │  Worker  │ │
                      │           └────┬─────┘ │
                      │                │       │
                      └────────────────┴───────┘
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
