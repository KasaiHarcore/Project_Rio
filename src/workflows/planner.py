"""Planner layer for the ReAct agent.

Runs BEFORE the main agent to pre-analyze user intent, select which
tools to activate, and generate a focused instruction. This keeps the
main agent's context lean by injecting only the selected tool guides.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field, field_validator

from utils.log import log_info, log_warning
from workflows.tool_registry import ToolRegistryEntry, get_planner_descriptions
from workflows.utils.message_utils import trim_messages_with_integrity


# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------


class PlannerOutput(BaseModel):
    """Structured output returned by the planner LLM node."""

    instruction: str = Field(
        description=(
            "1-3 sentence instruction for the main agent describing exactly what "
            "the user wants and how to handle it. For multi-part requests, break "
            "into numbered steps (e.g. '1. ... 2. ...'). Be specific: name which "
            "tool to use per step and what to do with the result."
        )
    )
    actions: List[str] = Field(
        description=(
            "List of tool names to activate for this turn. "
            "Use exact names from the available tools list. "
            "Can contain multiple names for multi-part requests. "
            "Duplicates are automatically removed."
        )
    )

    @field_validator("actions", mode="before")
    @classmethod
    def deduplicate_actions(cls, v: Any) -> Any:
        if not isinstance(v, list):
            return v
        return list(dict.fromkeys(v))


# ---------------------------------------------------------------------------
# Planner system prompt
# ---------------------------------------------------------------------------

PLANNER_SYSTEM_PROMPT = """\
## Analyze the user's message and decide:
1. What the main agent should do (instruction)
2. Which tools to activate (actions)

## Based on:
- USER_MESSAGE: Current user request
- CHAT_HISTORY: Previous user messages (oldest first)
- PREVIOUS_AI_MESSAGES: Recent AI response excerpts
- AVAILABLE_TOOLS: All available tools with descriptions

## Return JSON matching "PlannerOutput" schema:

1. "instruction": Write 1-3 specific sentences. For each step specify:
   - WHAT is the response language (match the user's language)
   - Which tools to use
   - HOW to use them (e.g. "Use delegate_mission_task to create a mission with title X")

2. "actions": the tool names from AVAILABLE_TOOLS

## MULTI-TOOL STRATEGY
In "instruction", specify execution strategy when multiple tools are needed:
- **parallel**: tools are independent, combine results (e.g. search + recall_memories)
- **sequential**: one tool's output feeds the next (e.g. web_search → web_extract)
- **iterative**: call tool, evaluate, decide next (e.g. search → if insufficient → web)

Default strategy:
- Simple lookups → single tool
- Information gathering → parallel
- Analytical/exploratory → sequential or iterative
- When in doubt → sequential

Keep "actions" minimal — list only the 1-2 starting tools. The main agent can call \
additional tools based on intermediate results.

## DELEGATION RULES
- For mission operations (create, update, list, complete, delete, toggle steps) → delegate_mission_task
- For note operations (create, search, update, delete, collections, graph) → delegate_note_task
- For SQL queries (admin) → delegate_sql_task
- For OS commands (admin) → delegate_os_task
- For greetings, thanks, goodbyes, or off-topic requests → set actions to empty list []

## IMPORTANT
- If USER_MESSAGE is standalone and clear → IGNORE CHAT_HISTORY, focus on USER_MESSAGE only.
- If USER_MESSAGE references past interactions or is ambiguous → USE CHAT_HISTORY to disambiguate.
- For memory operations (recall, store, forget) → use the appropriate memory tool directly.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_planner_user_content(
    current_user_message: str,
    chat_history: str,
    previous_ai_context: str,
    registry_descriptions: str,
) -> str:
    """Assemble the user-turn text sent to the planner LLM."""
    return (
        f"USER_MESSAGE:\n{current_user_message}\n\n"
        f"CHAT_HISTORY:\n{chat_history}\n\n"
        f"PREVIOUS_AI_MESSAGES:\n{previous_ai_context}\n\n"
        f"AVAILABLE_TOOLS:\n{registry_descriptions}"
    )


def _extract_text(content: Any) -> str:
    """Extract plain text from message content (str or list of dicts)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text", item.get("content", ""))))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content) if content else ""


# ---------------------------------------------------------------------------
# Planner node
# ---------------------------------------------------------------------------


def planner_node(
    state: Dict[str, Any],
    config: RunnableConfig,
) -> Dict[str, Any]:
    """LangGraph node: run the planner before the main agent.

    Reads the registry from ``config["configurable"]`` and returns
    ``{"instruction": ..., "actions": [...]}`` to the graph state.
    Fails open — returns empty instruction/actions on error.
    """
    configurable = (config or {}).get("configurable", {})
    planner_llm = configurable.get("planner_llm")
    registry: Dict[str, ToolRegistryEntry] = configurable.get("tool_registry", {})

    if not planner_llm:
        log_warning("[Planner] No planner LLM configured, skipping")
        return {"instruction": "", "actions": []}

    messages = state.get("messages") or []
    if not messages:
        return {"instruction": "", "actions": []}

    # Find latest human message
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    if not user_messages:
        return {"instruction": "", "actions": []}

    latest = user_messages[-1]
    current_text = _extract_text(latest.content).strip()

    # Build chat history context (trimmed)
    try:
        trimmed = trim_messages_with_integrity(messages, max_messages=10)
    except Exception:
        trimmed = messages

    prev_user = [m for m in trimmed if isinstance(m, HumanMessage)][:-1]
    chat_history = (
        "\n".join(
            f"{i+1}. {_extract_text(m.content).strip()}"
            for i, m in enumerate(prev_user)
        )
        if prev_user
        else "None"
    )

    ai_msgs = [m for m in trimmed if isinstance(m, AIMessage)]
    ai_context_parts = []
    for i, m in enumerate(ai_msgs):
        words = _extract_text(m.content).split()[:20]
        ai_context_parts.append(f"{i+1}. {' '.join(words)}")
    previous_ai_context = "\n".join(ai_context_parts) if ai_context_parts else "None"

    registry_descriptions = get_planner_descriptions(registry)

    user_content = _build_planner_user_content(
        current_user_message=current_text,
        chat_history=chat_history,
        previous_ai_context=previous_ai_context,
        registry_descriptions=registry_descriptions,
    )

    try:
        structured_llm = planner_llm.with_structured_output(schema=PlannerOutput)
        result: PlannerOutput = structured_llm.invoke([
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ])
        instruction = result.instruction or ""
        actions = result.actions or []
    except Exception as exc:
        log_warning(f"[Planner] Structured output failed (fail-open): {exc}")
        instruction = ""
        actions = []

    log_info(
        f"[Planner] instruction={instruction[:120]}… | actions={actions}"
    )
    return {"instruction": instruction, "actions": actions}
