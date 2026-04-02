"""ReAct agent tool registry.

Provides ``build_supervisor_tools()`` which constructs the supervisor's tool
list: direct tools (memory, search) + delegation tools (mission, note, sql, os).

Sub-agent tool builders are in their respective modules and are invoked lazily
by the delegation tools when first needed.
"""

from __future__ import annotations

from typing import Any, Optional

from core.settings import AgentConfig
from utils.log import log_info

from workflows.tools.search_tools import build_search_tools
from workflows.tools.memory_tools import build_memory_tools
from workflows.tools.delegation_tools import build_delegation_tools


def build_supervisor_tools(
    user_id: str,
    user_role: str,
    config: AgentConfig,
    store: Any = None,
) -> list:
    """Build the supervisor agent's tool list.

    The supervisor gets:
    - **Direct tools**: memory (recall/store/forget), search (documents, web, graph).
      These handle simple requests without sub-agent overhead.
    - **Delegation tools**: mission, note, sql (admin), os (admin).
      These invoke specialized ReAct sub-agents for domain operations.

    Args:
        user_id: Authenticated user identifier.
        user_role: User role — ``"user"`` or ``"admin"``.
        config: Agent configuration (mode, character, etc.).
        store: Optional PostgresStore for long-term memory tools.

    Returns:
        List of LangChain ``@tool`` functions for ``create_react_agent``.
    """
    tools: list = [
        # Direct tools — supervisor handles these itself
        *build_memory_tools(user_id, store),
        *build_search_tools(user_id),
        # Delegation tools — invoke sub-agents for domain operations
        *build_delegation_tools(user_id, user_role),
    ]

    log_info(
        f"[tools] Built {len(tools)} supervisor tools for user={user_id[:8]}… "
        f"role={user_role} mode={config.mode}"
    )
    return tools
