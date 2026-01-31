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
    │     │     │     │            │
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

from backend.utils.log import log_debug, log_error, log_info, log_success, log_warning
from backend.workflows.state import (
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
from backend.workflows.supervisor import SupervisorAgent
from backend.workflows.workers import (
    PlanningWorker,
    RetrievalWorker,
    SQLWorker,
    WebSearchWorker,
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
NODE_SYNTHESIZE = "synthesize"
NODE_HUMAN_CHECK = "human_check"


# =============================================================================
# Node Functions
# =============================================================================

def create_supervisor_node(supervisor: SupervisorAgent):
    """
    Create the supervisor node function.
    
    The supervisor analyzes the state and makes routing decisions.
    """
    def supervisor_node(state: AgentState) -> Dict[str, Any]:
        log_info("=== Supervisor Node ===")
        
        # Make routing decision
        decision = supervisor.route(state)
        
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


def create_synthesize_node(supervisor: SupervisorAgent):
    """
    Create the synthesis node function.
    
    Synthesizes gathered context into a final response.
    """
    def synthesize_node(state: AgentState) -> Dict[str, Any]:
        log_info("=== Synthesize Node ===")
        
        # Generate final response
        response = supervisor.generate_response(state)
        
        # Add response as AI message
        from langchain_core.messages import AIMessage
        messages = list(state.get("messages") or [])
        messages.append(AIMessage(content=response))
        
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
    interrupt_before: Optional[List[str]] = None,
    interrupt_after: Optional[List[str]] = None,
) -> CompiledStateGraph:
    """
    Build the multi-agent workflow graph.
    
    Args:
        config: Agent configuration
        checkpointer: Optional checkpointer for state persistence
        interrupt_before: Nodes to interrupt before (human-in-the-loop)
        interrupt_after: Nodes to interrupt after
    
    Returns:
        Compiled LangGraph workflow
    """
    log_info("Building multi-agent workflow graph")
    
    # Create agents
    supervisor = SupervisorAgent(config=config)
    
    # Create the graph
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node(NODE_SUPERVISOR, create_supervisor_node(supervisor))
    graph.add_node(NODE_PLANNING, create_worker_node(PlanningWorker, config))
    graph.add_node(NODE_RETRIEVAL, create_worker_node(RetrievalWorker, config))
    graph.add_node(NODE_WEB_SEARCH, create_worker_node(WebSearchWorker, config))
    graph.add_node(NODE_SQL, create_worker_node(SQLWorker, config))
    graph.add_node(NODE_SYNTHESIZE, create_synthesize_node(supervisor))
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
        NODE_SQL,
        route_after_worker,
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
    
    # Compile the graph
    compiled = graph.compile(
        checkpointer=checkpointer,
        interrupt_before=default_interrupt_before if default_interrupt_before else None,
        interrupt_after=default_interrupt_after if default_interrupt_after else None,
    )
    
    log_success("Workflow graph compiled successfully")
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
