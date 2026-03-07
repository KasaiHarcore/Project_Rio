"""
Multi-agent Supervisor-Worker Workflow Architecture.

This module implements a hierarchical agent system where:
- Supervisor: High-level control, routing, and decision-making
- Workers: Specialized single-task agents (Planning, Retrieval, Web Search, SQL, Memory, Note, Mission)

Key Features:
- Durable Execution with PostgreSQL checkpointing
- Human-in-the-loop support at any point
- Streaming support for real-time responses
- State persistence across sessions
- Long-term memory with semantic search

Architecture:
    User Question
         │
         ▼
    ┌─────────────┐
    │  Supervisor  │ ◄─── Main control loop
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │   Router    │ ◄─── Decides which worker(s) to invoke
    └──────┬──────┘
           │
    ┌──────┴──────────────────────────────────┐
    │              Workers                     │
    ├─────────┬──────────┬────────┬───────────┤
    │Planning │Retrieval │  Web   │ SQL  │Mem │Note│Mission│
    │ Worker  │ Worker   │ Search │Worker│    │    │       │
    └─────────┴──────────┴────────┴──────┴────┴────┴───────┘
           │
           ▼
    Final Response
"""

from workflows.state import (
    AgentState,
    WorkerResult,
    SupervisorDecision,
    HumanInterruptType,
    reset_execution_state,
)
from workflows.checkpointer import (
    checkpoint_context,
    get_checkpointer,
    build_config_payload,
)
from workflows.memory_store import (
    memory_store_context,
    get_memory_store,
    store_memory,
    search_memories,
    format_memories_for_prompt,
    MemoryNamespace,
)
from workflows.workers import (
    PlanningWorker,
    RetrievalWorker,
    WebSearchWorker,
    SQLWorker,
    MemoryWorker,
    NoteWorker,
    MissionWorker,
)
from workflows.supervisor import SupervisorAgent
from workflows.graph import build_workflow_graph
from workflows.executor import (
    run_workflow,
    stream_workflow,
    resume_sql_approval,
    list_checkpoints,
    load_checkpoint,
    resume_from_checkpoint,
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
    "MemoryWorker",
    "NoteWorker",
    "MissionWorker",
    # Supervisor
    "SupervisorAgent",
    # Graph
    "build_workflow_graph",
    # Executor (includes checkpoint helpers)
    "run_workflow",
    "stream_workflow",
    "resume_sql_approval",
    "list_checkpoints",
    "load_checkpoint",
    "resume_from_checkpoint",
]
