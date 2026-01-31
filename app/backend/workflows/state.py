"""
Agent State Management for Multi-agent Supervisor-Worker Architecture.

This module defines the shared state that flows through the entire workflow graph.
All workers and the supervisor read from and write to this state.

Key Design Principles:
- Immutable message history (append-only via add_messages)
- Clear separation between worker results and supervisor decisions
- Human-in-the-loop interruption points
- Full checkpoint support for durability
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Sequence, TypedDict, Annotated

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph.message import add_messages

from backend.core.settings import DEFAULT_MAX_ITERATIONS


# =============================================================================
# Enums and Constants
# =============================================================================

class WorkerType(str, Enum):
    """Types of specialized workers available."""
    PLANNING = "planning"
    RETRIEVAL = "retrieval"
    WEB_SEARCH = "web_search"
    SQL = "sql"


class SupervisorAction(str, Enum):
    """Actions the supervisor can take."""
    DELEGATE = "delegate"           # Delegate to a worker
    RESPOND = "respond"             # Generate final response
    CLARIFY = "clarify"             # Ask user for clarification
    REFLECT = "reflect"             # DEPRECATED: Supervisor now evaluates results directly
    WAIT_HUMAN = "wait_human"       # Wait for human input


class HumanInterruptType(str, Enum):
    """Types of human-in-the-loop interruptions."""
    APPROVAL = "approval"           # Requires approval to proceed
    INPUT = "input"                 # Requires additional input
    CLARIFICATION = "clarification" # Needs clarification
    CONFIRMATION = "confirmation"   # Needs confirmation of action


class ExecutionStatus(str, Enum):
    """Current execution status of the workflow."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# Data Classes for Structured Results
# =============================================================================

@dataclass
class WorkerResult:
    """Result from a worker agent execution."""
    worker_type: WorkerType
    success: bool
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "worker_type": self.worker_type.value,
            "success": self.success,
            "content": self.content,
            "metadata": self.metadata,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkerResult":
        """Create from dictionary."""
        return cls(
            worker_type=WorkerType(data["worker_type"]),
            success=data["success"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            error=data.get("error"),
            execution_time_ms=data.get("execution_time_ms", 0),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
        )


@dataclass
class SupervisorDecision:
    """Decision made by the supervisor."""
    action: SupervisorAction
    next_worker: Optional[WorkerType] = None
    reasoning: str = ""
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "action": self.action.value,
            "next_worker": self.next_worker.value if self.next_worker else None,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SupervisorDecision":
        """Create from dictionary."""
        next_worker = WorkerType(data["next_worker"]) if data.get("next_worker") else None
        return cls(
            action=SupervisorAction(data["action"]),
            next_worker=next_worker,
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
        )


@dataclass
class HumanInterrupt:
    """Human-in-the-loop interruption request."""
    interrupt_type: HumanInterruptType
    message: str
    options: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "interrupt_type": self.interrupt_type.value,
            "message": self.message,
            "options": self.options,
            "context": self.context,
            "required": self.required,
        }


@dataclass
class ExecutionPlan:
    """Execution plan created by the planning worker."""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: str = ""
    estimated_workers: List[WorkerType] = field(default_factory=list)
    complexity: Literal["simple", "moderate", "complex"] = "simple"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "steps": self.steps,
            "reasoning": self.reasoning,
            "estimated_workers": [w.value for w in self.estimated_workers],
            "complexity": self.complexity,
        }


# =============================================================================
# Main Agent State (TypedDict for LangGraph)
# =============================================================================

class AgentState(TypedDict, total=False):
    """
    Shared state for the multi-agent workflow.
    
    This state flows through all nodes in the LangGraph workflow.
    The `messages` field uses the add_messages annotation for proper
    message accumulation during checkpointing.
    
    Attributes:
        schema_version: Version of the state schema for migrations
        messages: Conversation messages (append-only)
        
        # User Context
        original_question: The user's original question
        thread_id: Unique thread identifier
        user_id: User identifier (optional)
        mode: Execution mode (rag, web, chat, sql)
        
        # Execution State
        status: Current execution status
        current_worker: Currently executing worker (if any)
        iteration_count: Number of supervisor iterations
        max_iterations: Maximum allowed iterations
        
        # Planning
        execution_plan: The current execution plan
        plan_completed_steps: Steps that have been completed
        
        # Worker Results
        worker_results: Results from all worker executions
        gathered_context: Aggregated context from workers
        
        # Supervisor State
        supervisor_decisions: History of supervisor decisions
        final_response: The final response to the user
        
        # Human-in-the-loop
        pending_human_interrupt: Current pending human interrupt
        human_responses: History of human responses
        
        # Error Handling
        error: Current error (if any)
        retry_count: Number of retries attempted
        
        # Metadata
        metadata: Additional execution metadata
        timing: Timing information for phases
    """
    
    # Schema versioning for state migrations
    schema_version: int
    
    # Core message history - uses add_messages for proper append semantics
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # User Context
    original_question: str
    thread_id: str
    user_id: Optional[str]
    mode: Literal["rag", "web", "chat", "sql"]
    
    # Execution State
    status: ExecutionStatus
    current_worker: Optional[WorkerType]
    iteration_count: int
    max_iterations: int
    
    # Planning
    execution_plan: Optional[ExecutionPlan]
    plan_completed_steps: List[int]
    
    # Worker Results
    worker_results: List[WorkerResult]
    gathered_context: str
    
    # Supervisor State
    supervisor_decisions: List[SupervisorDecision]
    final_response: Optional[str]
    
    # Human-in-the-loop
    pending_human_interrupt: Optional[HumanInterrupt]
    human_responses: List[Dict[str, Any]]
    
    # Error Handling
    error: Optional[str]
    retry_count: int
    
    # Metadata
    metadata: Dict[str, Any]
    timing: Dict[str, int]


# =============================================================================
# State Factory Functions
# =============================================================================

def create_initial_state(
    *,
    question: str,
    thread_id: str,
    mode: Literal["rag", "web", "chat", "sql"] = "chat",
    user_id: Optional[str] = None,
    history: Optional[List[BaseMessage]] = None,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    metadata: Optional[Dict[str, Any]] = None,
) -> AgentState:
    """
    Create the initial state for a new workflow execution.
    
    Args:
        question: The user's question
        thread_id: Unique thread identifier
        mode: Execution mode
        user_id: Optional user identifier
        history: Optional conversation history
        max_iterations: Maximum supervisor iterations
        metadata: Optional additional metadata
    
    Returns:
        Initialized AgentState
    """
    messages: List[BaseMessage] = []
    
    # Add history if provided
    if history:
        messages.extend(history)
    
    # Add the current question
    messages.append(HumanMessage(content=question))
    
    return AgentState(
        schema_version=1,
        messages=messages,
        original_question=question,
        thread_id=thread_id,
        user_id=user_id,
        mode=mode,
        status=ExecutionStatus.PENDING,
        current_worker=None,
        iteration_count=0,
        max_iterations=max_iterations,
        execution_plan=None,
        plan_completed_steps=[],
        worker_results=[],
        gathered_context="",
        supervisor_decisions=[],
        final_response=None,
        pending_human_interrupt=None,
        human_responses=[],
        error=None,
        retry_count=0,
        metadata=metadata or {},
        timing={},
    )


def reset_execution_state(
    state: AgentState,
    *,
    new_question: str,
    mode: Literal["rag", "web", "chat", "sql"] = "chat",
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    metadata: Optional[Dict[str, Any]] = None,
) -> AgentState:
    """
    Reset execution state for a new message while preserving conversation history.
    
    This is used when continuing a conversation in the same thread.
    The message history is preserved, but all execution state is reset.
    
    Args:
        state: The current state (from checkpoint)
        new_question: The new user question
        mode: Execution mode
        max_iterations: Maximum supervisor iterations
        metadata: Optional additional metadata
    
    Returns:
        Reset AgentState ready for new execution
    """
    # Preserve message history, add new question
    messages = list(state.get("messages") or [])
    messages.append(HumanMessage(content=new_question))
    
    return AgentState(
        schema_version=state.get("schema_version", 1),
        messages=messages,
        original_question=new_question,
        thread_id=state.get("thread_id", ""),
        user_id=state.get("user_id"),
        mode=mode,
        # Reset all execution state
        status=ExecutionStatus.PENDING,
        current_worker=None,
        iteration_count=0,
        max_iterations=max_iterations,
        execution_plan=None,
        plan_completed_steps=[],
        worker_results=[],
        gathered_context="",
        supervisor_decisions=[],
        final_response=None,  # CRITICAL: Reset this!
        pending_human_interrupt=None,
        human_responses=[],
        error=None,
        retry_count=0,
        metadata=metadata or {},
        timing={},
    )


def build_messages_from_history(
    history: Optional[List[Dict[str, Any]]],
) -> List[BaseMessage]:
    """
    Convert raw history dictionaries to LangChain messages.
    
    Args:
        history: List of message dictionaries with 'role' and 'content'
    
    Returns:
        List of BaseMessage objects
    """
    messages: List[BaseMessage] = []
    
    for item in history or []:
        if not item:
            continue
        
        role = (item or {}).get("role", "user")
        content = (item or {}).get("content", "")
        
        if not content:
            continue
        
        if role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "tool":
            tool_call_id = (item or {}).get("tool_call_id", "tool")
            messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))
        elif role == "system":
            messages.append(SystemMessage(content=content))
        else:
            messages.append(HumanMessage(content=content))
    
    return messages


def extract_answer_from_state(state: AgentState) -> str:
    """
    Extract the final answer from the state.
    
    Priority:
    1. final_response if set
    2. Last AIMessage content
    3. Empty string
    """
    if state.get("final_response"):
        return state["final_response"]
    
    messages = state.get("messages") or []
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            return str(msg.content or "")
    
    return ""


def get_gathered_context(state: AgentState) -> str:
    """
    Get all gathered context from worker results.
    
    Returns:
        Combined context string from all successful worker results
    """
    context_parts: List[str] = []
    
    for result in state.get("worker_results") or []:
        if result.success and result.content:
            header = f"=== {result.worker_type.value.upper()} RESULT ==="
            context_parts.append(f"{header}\n{result.content}")
    
    return "\n\n".join(context_parts)


def should_interrupt_for_human(state: AgentState) -> bool:
    """Check if we should interrupt for human input."""
    interrupt = state.get("pending_human_interrupt")
    return interrupt is not None and interrupt.required


def is_execution_complete(state: AgentState) -> bool:
    """Check if the workflow execution is complete."""
    status = state.get("status")
    return status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED)


def has_exceeded_iterations(state: AgentState) -> bool:
    """Check if we've exceeded the maximum iterations."""
    current = state.get("iteration_count", 0)
    maximum = state.get("max_iterations", DEFAULT_MAX_ITERATIONS)
    return current >= maximum
