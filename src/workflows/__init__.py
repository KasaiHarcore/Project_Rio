"""
ReAct Supervisor + Sub-Agent Workflow Architecture.

This module implements a ReAct supervisor agent that delegates to
specialized sub-agents for domain operations (missions, notes, SQL, OS).

Architecture:
    User Question
         |
         v
    +-----------------+
    | Input Guardrail | <-- deterministic checks
    +-----------------+
         |
         v
    +--------------------+
    | ReAct Supervisor   | <-- thinks, plans, delegates
    |  direct tools:     |     memory, search
    |  delegation tools: |     mission, note, sql, os sub-agents
    +--------------------+
         |
         v
    +-----------------+
    |  Post-Process   | <-- background: memory, emotional engine
    +-----------------+
         |
         v
    +-----------------+
    | Output Guardrail| <-- PII + system leak regex
    +-----------------+
         |
         v
    Final Response
"""

from workflows.state import (
    AgentState,
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
from workflows.react_graph import build_react_graph
from workflows.executor import (
    run_workflow,
    stream_workflow,
    resume_sql_approval,
    list_checkpoints,
    load_checkpoint,
    resume_from_checkpoint,
)

__all__ = [
    "AgentState",
    "HumanInterruptType",
    "reset_execution_state",
    "checkpoint_context",
    "get_checkpointer",
    "build_config_payload",
    "memory_store_context",
    "get_memory_store",
    "store_memory",
    "search_memories",
    "format_memories_for_prompt",
    "MemoryNamespace",
    "build_react_graph",
    "run_workflow",
    "stream_workflow",
    "resume_sql_approval",
    "list_checkpoints",
    "load_checkpoint",
    "resume_from_checkpoint",
]
