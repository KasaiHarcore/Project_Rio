"""Dual tool registry for the planner + agent architecture.

Each entry has two text fields:
  - **description** (brief): shown to the planner — WHEN to use.
  - **guide** (detailed): injected into the main agent — HOW to use.

The planner sees only descriptions (cheap). The main agent receives only
the guides for planner-selected tools (focused context).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from utils.log import log_info


@dataclass(frozen=True)
class ToolRegistryEntry:
    """A single tool in the registry."""

    name: str
    description: str       # Brief — shown to planner (WHEN to use)
    guide: str             # Detailed — injected into agent (HOW to use)
    admin_only: bool = False


# ---------------------------------------------------------------------------
# Per-tool descriptions (WHEN) and guides (HOW)
# ---------------------------------------------------------------------------

_TOOL_ENTRIES: Dict[str, dict] = {
    # ── Memory tools ──
    "recall_memories": {
        "description": (
            "Search long-term memory about Sensei. Use when the user references "
            "past conversations, preferences, or personal facts."
        ),
        "guide": (
            "## Tool: recall_memories\n\n"
            "Search long-term memory for facts, experiences, or skills related to Sensei.\n"
            "- Pass a descriptive `query` string (not just a keyword).\n"
            "- `limit` defaults to 5. Increase for broad queries.\n"
            "- Results are JSON. Summarise relevantly — do not dump raw JSON."
        ),
    },
    "store_memory": {
        "description": (
            "Store a new fact, experience, or skill in long-term memory. "
            "Use when Sensei shares personal info worth remembering."
        ),
        "guide": (
            "## Tool: store_memory\n\n"
            "Store a fact or experience for future recall.\n"
            "- `text`: a clear, self-contained statement (include context).\n"
            "- `memory_type`: 'semantic' (facts), 'episodic' (experiences), 'procedural' (how-to).\n"
            "- Confirm to Sensei what you stored."
        ),
    },
    "forget_memory": {
        "description": (
            "Delete memories matching a topic. Use when Sensei asks you to "
            "forget something or correct stored information."
        ),
        "guide": (
            "## Tool: forget_memory\n\n"
            "Delete memories matching a query.\n"
            "- `query`: descriptive topic string.\n"
            "- Confirm deletion to Sensei."
        ),
    },
    # ── Search tools ──
    "web_search": {
        "description": (
            "Search the internet for current or external information. "
            "Use for news, facts not in internal docs, or when Sensei asks to search online."
        ),
        "guide": (
            "## Tool: web_search\n\n"
            "Internet search via Tavily.\n"
            "- `query`: clear search query.\n"
            "- `max_results`: default 5, max 20.\n"
            "- `topic`: 'general' or 'news'.\n"
            "- `search_depth`: 'basic' (fast) or 'advanced' (thorough).\n"
            "- Optional: `start_date`/`end_date` as YYYY-MM-DD for time filtering.\n"
            "- Budget: ~6 web_search calls per conversation. Use judiciously.\n"
            "- ALWAYS include clickable [Title](URL) links for every source."
        ),
    },
    "web_extract": {
        "description": (
            "Extract full page content from URLs. Use AFTER web_search when "
            "snippets are insufficient, or when Sensei provides specific URLs."
        ),
        "guide": (
            "## Tool: web_extract\n\n"
            "Read full content from web pages.\n"
            "- `urls`: list of up to 5 URLs.\n"
            "- `extract_depth`: 'basic' or 'advanced'.\n"
            "- Optional `query` to focus extraction.\n"
            "- Budget: ~4 web_extract calls per conversation.\n"
            "- When Sensei provides a URL directly, use this tool (skip web_search)."
        ),
    },
    "search_documents": {
        "description": (
            "Search internal documents and knowledge base via vector DB. "
            "Use for information that should be in uploaded/indexed documents."
        ),
        "guide": (
            "## Tool: search_documents\n\n"
            "Semantic search over internal documents (Qdrant).\n"
            "- `query`: descriptive search query.\n"
            "- `k`: number of results (default 5).\n"
            "- ALWAYS cite source: **Source:** filename — Page X, Chunk Y.\n"
            "- Include ALL metadata returned by the tool."
        ),
    },
    "search_knowledge_graph": {
        "description": (
            "Search the Neo4j knowledge graph for entity relationships. "
            "Use for 'how is X related to Y' or entity exploration queries."
        ),
        "guide": (
            "## Tool: search_knowledge_graph\n\n"
            "Query entity relationships in Neo4j.\n"
            "- `query`: natural language query about entities/relationships.\n"
            "- `depth`: traversal depth (default 2).\n"
            "- Results are structured graph data — explain relationships clearly."
        ),
    },
    # ── Delegation tools ──
    "delegate_mission_task": {
        "description": (
            "Delegate mission/goal/task operations to the Mission Sub-Agent. "
            "Use for ALL mission CRUD: create, update, toggle steps, complete, "
            "delete, query progress, list missions."
        ),
        "guide": (
            "## Tool: delegate_mission_task\n\n"
            "Invoke the Mission Sub-Agent.\n"
            "- `instruction`: CLEAR, COMPLETE instruction. Include ALL relevant details "
            "(names, IDs, values, dates) — the sub-agent has NO conversation context.\n"
            "- For multi-step operations, be explicit about each step.\n"
            "- After receiving the result, respond in your own voice — do NOT repeat raw output."
        ),
    },
    "delegate_note_task": {
        "description": (
            "Delegate note operations to the Note Sub-Agent. "
            "Use for ALL note CRUD: create, search, update, delete, collections, "
            "graph navigation, backlinks, todos."
        ),
        "guide": (
            "## Tool: delegate_note_task\n\n"
            "Invoke the Note Sub-Agent.\n"
            "- `instruction`: CLEAR, COMPLETE instruction with all relevant details.\n"
            "- For search: specify what to find and any filters.\n"
            "- For creation: include title, content, tags, collection if mentioned.\n"
            "- After receiving the result, respond in your own voice."
        ),
    },
    "delegate_flashcard_task": {
        "description": (
            "Delegate flashcard/study-card operations to the Flashcard Sub-Agent. "
            "Use for creating decks, generating flashcards from notes, reviewing cards, "
            "listing due cards, study stats, or when the user wants to study/quiz/make flashcards."
        ),
        "guide": (
            "## Tool: delegate_flashcard_task\n\n"
            "Invoke the Flashcard Sub-Agent.\n"
            "- `instruction`: CLEAR, COMPLETE instruction with all relevant details.\n"
            "- For generating from notes: include note_id and deck_id (or deck name).\n"
            "- For creating cards: include front (question) and back (answer) text.\n"
            "- For review sessions: specify deck or 'all due cards'.\n"
            "- After receiving the result, respond in your own voice."
        ),
    },
    "delegate_automation_task": {
        "description": (
            "Delegate scheduled automation operations to the Automation Sub-Agent. "
            "Use when the user wants to set up reminders, schedule recurring agent tasks, "
            "create daily/weekly automations, enable/disable automations, or run one manually. "
            "Keywords: remind, schedule, every day, every week, automate, recurring, cron."
        ),
        "guide": (
            "## Tool: delegate_automation_task\n\n"
            "Invoke the Automation Sub-Agent.\n"
            "- `instruction`: CLEAR, COMPLETE instruction with all details.\n"
            "- For creating: include schedule (e.g. 'every day at 9am'), what to do, "
            "and any preferences (timezone, delivery method).\n"
            "- For updating: include the automation ID and what to change.\n"
            "- Common cron patterns the sub-agent understands:\n"
            "  - 'every hour' -> '0 * * * *'\n"
            "  - 'every day at 9am' -> '0 9 * * *'\n"
            "  - 'every Monday' -> '0 9 * * 1'\n"
            "  - 'weekdays at 9am' -> '0 9 * * 1-5'\n"
            "- After receiving the result, respond in your own voice."
        ),
    },
    "delegate_audio_task": {
        "description": (
            "Delegate audio overview/podcast generation to the Audio Sub-Agent. "
            "Use when the user wants to generate audio from notes, create a podcast "
            "or lecture from study materials, listen to their notes as audio, "
            "or check audio generation status. "
            "Keywords: audio, podcast, lecture, listen, speak, read aloud, audio summary."
        ),
        "guide": (
            "## Tool: delegate_audio_task\n\n"
            "Invoke the Audio Sub-Agent.\n"
            "- `instruction`: CLEAR, COMPLETE instruction with all details.\n"
            "- Include source note IDs if the user mentioned specific notes.\n"
            "- If user says 'my notes about X', first use delegate_note_task to search "
            "for those notes, get their IDs, then call this tool with those IDs.\n"
            "- Available formats: summary (conversational), dialogue (teacher-student), "
            "lecture (academic).\n"
            "- Audio generation is async -- tell the user it will be ready shortly.\n"
            "- After receiving the result, respond in your own voice."
        ),
    },
    "delegate_sql_task": {
        "description": (
            "Delegate SQL database queries to the SQL Sub-Agent (admin only). "
            "Use for database exploration, schema queries, or data analysis."
        ),
        "guide": (
            "## Tool: delegate_sql_task\n\n"
            "Invoke the SQL Sub-Agent (admin only).\n"
            "- `instruction`: describe what data to find or query to run.\n"
            "- The sub-agent can describe schema and execute SELECT queries.\n"
            "- After receiving results, present data clearly."
        ),
        "admin_only": True,
    },
    "delegate_os_task": {
        "description": (
            "Delegate OS/shell commands to the OS Control Sub-Agent (admin only). "
            "Use for system commands, file operations, or process management."
        ),
        "guide": (
            "## Tool: delegate_os_task\n\n"
            "Invoke the OS Control Sub-Agent (admin only).\n"
            "- `instruction`: describe the command or operation.\n"
            "- Commands are risk-classified — the sub-agent handles safety."
        ),
        "admin_only": True,
    },
}


# ---------------------------------------------------------------------------
# Registry builder (cached per role — registry is static at runtime)
# ---------------------------------------------------------------------------

_REGISTRY_CACHE: Dict[str, Dict[str, ToolRegistryEntry]] = {}
_PLANNER_DESC_CACHE: Dict[str, str] = {}


def build_tool_registry(user_role: str = "user") -> Dict[str, ToolRegistryEntry]:
    """Build the full tool registry (cached per user_role).

    Admin-only tools are excluded when ``user_role != "admin"``.
    """
    if user_role in _REGISTRY_CACHE:
        return _REGISTRY_CACHE[user_role]

    registry: Dict[str, ToolRegistryEntry] = {}

    for tool_name, entry in _TOOL_ENTRIES.items():
        is_admin = entry.get("admin_only", False)
        if is_admin and user_role != "admin":
            continue
        registry[tool_name] = ToolRegistryEntry(
            name=tool_name,
            description=entry["description"],
            guide=entry["guide"],
            admin_only=is_admin,
        )

    log_info(
        f"[ToolRegistry] Built registry: {len(registry)} tools "
        f"for role={user_role}"
    )
    _REGISTRY_CACHE[user_role] = registry
    return registry


def get_planner_descriptions(registry: Dict[str, ToolRegistryEntry]) -> str:
    """Format all registry descriptions for injection into the planner prompt.

    Returns a numbered list: ``1. **name**: description``
    Cached — the output is static for a given registry instance.
    """
    cache_key = id(registry)
    cached = _PLANNER_DESC_CACHE.get(str(cache_key))
    if cached is not None:
        return cached

    lines = []
    for idx, (name, entry) in enumerate(registry.items(), start=1):
        lines.append(f"{idx}. **{name}**: {entry.description}")
    result = "\n".join(lines)
    _PLANNER_DESC_CACHE[str(cache_key)] = result
    return result


def build_selected_guides(
    actions: list[str],
    registry: Dict[str, ToolRegistryEntry],
) -> str:
    """Format guides for planner-selected actions only.

    Returns the detailed HOW-TO guides for the main agent, plus a compact
    reference section for all other available tools.
    """
    parts: list[str] = []
    seen: set = set()

    for action_name in actions:
        if action_name in seen:
            continue
        seen.add(action_name)
        entry = registry.get(action_name)
        if not entry:
            continue
        parts.append(f"**Tool: {action_name}**\n\n{entry.guide}")

    # Compact reference for other tools (so agent can discover them mid-reasoning)
    other_lines = [
        f"- **{name}**: {entry.description[:150]}"
        for name, entry in registry.items()
        if name not in seen
    ]
    if other_lines:
        parts.append(
            "## OTHER AVAILABLE TOOLS (use if primary tools are insufficient)\n"
            + "\n".join(other_lines)
        )

    return "\n\n".join(parts)
