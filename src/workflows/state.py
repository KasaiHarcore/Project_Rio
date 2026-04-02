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

from core.settings import DEFAULT_MAX_ITERATIONS

class UserStage(str, Enum):
    """What stage the user is in within their work lifecycle."""
    EXPLORE = "explore"
    UNDERSTAND = "understand"
    PLAN = "plan"
    EXECUTE = "execute"
    REVIEW = "review"
    RETAIN = "retain"


class InterventionType(str, Enum):
    """What kind of help Rio should provide right now."""
    TEACH = "teach"
    CLARIFY = "clarify"
    CHALLENGE = "challenge"
    BREAK_DOWN = "break_down"
    PLAN = "plan"
    RETRIEVE_EVIDENCE = "retrieve_evidence"
    DRAFT_STRUCTURE = "draft_structure"
    COMMIT_STRUCTURE = "commit_structure"
    REVIEW_PROGRESS = "review_progress"
    SUMMARIZE_LEARNING = "summarize_learning"
    RECOMMEND_NEXT_STEP = "recommend_next_step"


@dataclass
class SupportState:
    """Support-layer state for AI-first orchestration.

    Captures what Rio understands about the user's current situation,
    what intervention is needed, and what to recommend next.
    """
    primary_goal: Optional[str] = None
    current_stage: Optional[UserStage] = None
    current_friction: Optional[str] = None
    recommended_next_step: Optional[str] = None
    current_intervention: Optional[InterventionType] = None
    intervention_reasoning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_goal": self.primary_goal,
            "current_stage": self.current_stage.value if self.current_stage else None,
            "current_friction": self.current_friction,
            "recommended_next_step": self.recommended_next_step,
            "current_intervention": self.current_intervention.value if self.current_intervention else None,
            "intervention_reasoning": self.intervention_reasoning,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SupportState":
        return cls(
            primary_goal=data.get("primary_goal"),
            current_stage=UserStage(data["current_stage"]) if data.get("current_stage") else None,
            current_friction=data.get("current_friction"),
            recommended_next_step=data.get("recommended_next_step"),
            current_intervention=InterventionType(data["current_intervention"]) if data.get("current_intervention") else None,
            intervention_reasoning=data.get("intervention_reasoning"),
        )


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


class AgentState(TypedDict, total=False):
    """
    Shared state for the multi-agent workflow.
    
    This state flows through all nodes in the LangGraph workflow.
    The `messages` field uses the add_messages annotation for proper
    message accumulation during checkpointing.
    
    Attributes:
        schema_version: Version of the state schema for migrations
        messages: Conversation messages (append-only)
        
        original_question: The user's original question
        thread_id: Unique thread identifier
        user_id: User identifier (optional)
        mode: Execution mode (rag, web, chat, sql)
        
        status: Current execution status
        current_worker: Currently executing worker (if any)
        iteration_count: Number of supervisor iterations
        max_iterations: Maximum allowed iterations
        
        execution_plan: The current execution plan
        plan_completed_steps: Steps that have been completed
        
        worker_results: Results from all worker executions
        gathered_context: Aggregated context from workers
        
        supervisor_decisions: History of supervisor decisions
        final_response: The final response to the user
        
        pending_human_interrupt: Current pending human interrupt
        human_responses: History of human responses
        
        error: Current error (if any)
        retry_count: Number of retries attempted
        
        metadata: Additional execution metadata
        timing: Timing information for phases
    """
    
    schema_version: int
    
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    original_question: str
    thread_id: str
    user_id: Optional[str]
    mode: Literal["rag", "web", "chat", "sql"]
    
    status: ExecutionStatus
    current_worker: Optional[str]
    iteration_count: int
    max_iterations: int
    
    execution_plan: Optional[Dict[str, Any]]
    plan_completed_steps: List[int]
    
    worker_results: List[Dict[str, Any]]
    gathered_context: str

    completed_actions: List[Dict[str, Any]]
    
    supervisor_decisions: List[Dict[str, Any]]
    final_response: Optional[str]
    
    pending_human_interrupt: Optional[HumanInterrupt]
    human_responses: List[Dict[str, Any]]
    
    pending_sql_approval: Optional[Dict[str, Any]]  # Serialized PendingSQLApproval
    sql_approval_history: List[Dict[str, Any]]  # Serialized SQLApprovalHistory list
    sql_schema_context: Optional[str]  # Cached schema context for LLM
    
    error: Optional[str]
    retry_count: int
    
    metadata: Dict[str, Any]
    timing: Dict[str, int]

    emotional_context: Optional[Dict[str, Any]]

    support_state: Optional[SupportState]

    guardrail_passed: Optional[bool]
    guardrail_rejection: Optional[str]
    guardrail_output_passed: Optional[bool]
    guardrail_output_rejection: Optional[str]


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
    
    if history:
        messages.extend(history)
    
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
        pending_sql_approval=None,
        sql_approval_history=[],
        sql_schema_context=None,
        emotional_context=None,
        support_state=None,
        guardrail_passed=None,
        guardrail_rejection=None,
        guardrail_output_passed=None,
        guardrail_output_rejection=None,
        completed_actions=[],
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
    messages = list(state.get("messages") or [])
    messages.append(HumanMessage(content=new_question))
    
    return AgentState(
        schema_version=state.get("schema_version", 1),
        messages=messages,
        original_question=new_question,
        thread_id=state.get("thread_id", ""),
        user_id=state.get("user_id"),
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
        final_response=None,  # CRITICAL: Reset this!
        pending_human_interrupt=None,
        human_responses=[],
        error=None,
        retry_count=0,
        metadata=metadata or {},
        timing={},
        pending_sql_approval=None,
        sql_approval_history=state.get("sql_approval_history", []),
        sql_schema_context=state.get("sql_schema_context"),  # Keep cached schema
        emotional_context=None,
        support_state=None,
        guardrail_passed=None,
        guardrail_rejection=None,
        guardrail_output_passed=None,
        guardrail_output_rejection=None,
        completed_actions=[],
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


