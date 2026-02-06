"""
Multi-agent Supervisor-Worker Workflow Architecture.

This module implements a hierarchical agent system where:
- Supervisor: High-level control, routing, and decision-making
- Workers: Specialized single-task agents (Planning, Retrieval, Web Search, SQL)

Key Features:
- Durable Execution with PostgreSQL checkpointing
- Human-in-the-loop support at any point
- Streaming support for real-time responses
- State persistence across sessions

Architecture:
    User Question
         │
         ▼
    ┌─────────────┐
    │  Supervisor │ ◄─── Main control loop
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │   Router    │ ◄─── Decides which worker(s) to invoke
    └──────┬──────┘
           │
    ┌──────┴──────────────────────┐
    │         Workers             │
    ├─────────┬─────────┬────────┤
    │Planning │Retrieval│  Web   │ SQL  │
    │ Worker  │ Worker  │ Search │Worker│
    └─────────┴─────────┴────────┴──────┘
           │
           ▼
    Final Response
"""

from backend.application.workflows.state import (
    AgentState,
    WorkerResult,
    SupervisorDecision,
    HumanInterruptType,
    reset_execution_state,
)
from backend.application.workflows.checkpointer import (
    checkpoint_context,
    get_checkpointer,
    build_config_payload,
)
from backend.application.workflows.memory_store import (
    memory_store_context,
    get_memory_store,
    store_memory,
    search_memories,
    format_memories_for_prompt,
    MemoryNamespace,
)
from backend.application.workflows.workers import (
    PlanningWorker,
    RetrievalWorker,
    WebSearchWorker,
    SQLWorker,
)
from backend.application.workflows.supervisor import SupervisorAgent
from backend.application.workflows.graph import build_workflow_graph
from backend.application.workflows.executor import (
    run_workflow,
    stream_workflow,
    list_checkpoints,
    load_checkpoint,
    resume_from_checkpoint,
)
from backend.core.settings import (
    TOOL_PREVIEW_LENGTH,
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_CHECKPOINT_NS,
    WORKER_TIMEOUT_SECONDS,
    MAX_CONTEXT_LENGTH,
    MAX_RESPONSE_LENGTH,
    STREAM_TOKEN_BATCH_SIZE,
    HUMAN_INTERRUPT_TIMEOUT,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    RETRY_BACKOFF_MAX,
)

__all__ = [
    # State
    "AgentState",
    "WorkerResult",
    "SupervisorDecision",
    "HumanInterruptType",
    "reset_execution_state",
    # Checkpointing (short-term memory)
    "checkpoint_context",
    "get_checkpointer",
    "build_config_payload",
    # Memory Store (long-term memory)
    "memory_store_context",
    "get_memory_store",
    "store_memory",
    "search_memories",
    "format_memories_for_prompt",
    "MemoryNamespace",
    # Workers
    "PlanningWorker",
    "RetrievalWorker",
    "WebSearchWorker",
    "SQLWorker",
    # Supervisor
    "SupervisorAgent",
    # Graph
    "build_workflow_graph",
    # Executor (includes checkpoint helpers)
    "run_workflow",
    "stream_workflow",
    "list_checkpoints",
    "load_checkpoint",
    "resume_from_checkpoint",
    # Constants
    "TOOL_PREVIEW_LENGTH",
    "DEFAULT_MAX_ITERATIONS",
    "DEFAULT_CHECKPOINT_NS",
    "WORKER_TIMEOUT_SECONDS",
    "MAX_CONTEXT_LENGTH",
    "MAX_RESPONSE_LENGTH",
    "STREAM_TOKEN_BATCH_SIZE",
    "HUMAN_INTERRUPT_TIMEOUT",
    "MAX_RETRIES",
    "RETRY_BACKOFF_BASE",
    "RETRY_BACKOFF_MAX",
]
