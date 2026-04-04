"""Per-domain ReAct sub-agent builders.

Each builder creates a compiled ``create_react_agent`` graph with a focused
tool set and domain-specific system prompt.  The supervisor's delegation
tools invoke these sub-agents synchronously.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from langgraph.prebuilt import create_react_agent

from infrastructure.llm import form
from utils.log import log_info

# ---------------------------------------------------------------------------
# Sub-agent system prompts (concise — persona voice is NOT here; the
# supervisor applies persona when synthesizing the sub-agent's result)
# ---------------------------------------------------------------------------

_MISSION_AGENT_PROMPT = """\
You are a mission management agent. You handle mission/goal/task operations.

Rules:
- ALWAYS call list_missions first to see real data with IDs and step indices.
- Use the exact mission_id and step_index from list results — never guess.
- For toggle/complete/update/delete: confirm the target exists before mutating.
- Return a concise JSON-like summary of what you did and the result.
- If something fails, return the error clearly.
"""

_NOTE_AGENT_PROMPT = """\
You are a note management agent. You handle note CRUD, search, and graph operations.

Rules:
- For updates/deletes: call search_notes or get_note first to find the exact note_id.
- For creates: check for duplicates with search_notes before creating.
- Return a concise summary of what you did, including note_id for mutations.
- If something fails, return the error clearly.
"""

_SQL_AGENT_PROMPT = """\
You are a database query agent. You handle SQL operations.

Rules:
- ALWAYS call describe_database_schema first to understand the schema.
- Write precise, efficient SQL with WHERE clauses and LIMIT.
- Read queries execute immediately. Write queries require user approval.
- Return query results formatted as a readable table or summary.
- Never fabricate schema — only use tables/columns from describe_database_schema.
"""

_FLASHCARD_AGENT_PROMPT = """\
You are a flashcard management agent. You handle flashcard and spaced repetition operations.

Rules:
- For generating flashcards from a note, call generate_flashcards_from_note with note_id and deck_id.
- For listing due cards, call get_due_flashcards.
- For listing decks, call list_flashcard_decks first to get deck IDs.
- For creating cards manually, call create_flashcard with front/back text.
- If no deck exists yet, create one first with create_flashcard_deck.
- Return a concise summary of what you did and the result.
"""


_AUTOMATION_AGENT_PROMPT = """\
You are an automation management agent. You handle scheduled task operations.

Rules:
- ALWAYS call list_automations first to see existing automations with IDs.
- For cron expressions, use standard format: minute hour day month weekday.
  Common examples: '0 9 * * *' (daily 9am), '0 * * * *' (every hour),
  '0 9 * * 1' (Monday 9am), '0 9 * * 1-5' (weekdays 9am).
- When creating, write clear agent_instruction prompts that describe what Rio should do.
- For enable/disable: use update_automation with enabled=true/false.
- Return a concise summary of what you did.
"""

_AUDIO_AGENT_PROMPT = """\
You are an audio overview agent. You generate spoken audio from study materials.

Rules:
- To generate audio, you need source_ids (note IDs or flashcard IDs).
- If the user says "my notes about X", first search for those notes using context,
  then pass the note IDs to generate_audio_overview.
- Available formats: "summary" (conversational), "dialogue" (teacher-student),
  "lecture" (structured academic).
- Audio generation is async — tell the user it will be ready in a few minutes.
- Return a concise summary of what you started.
"""

_OS_AGENT_PROMPT = """\
You are an OS control agent. You execute shell commands.

Rules:
- Prefer read-only commands for diagnostics (ls, cat, ps, df, etc.).
- Avoid interactive commands (vim, top, ssh without -t).
- High-risk commands will require user approval.
- Return the command, exit code, and relevant output.
"""


# ---------------------------------------------------------------------------
# Sub-agent builders
# ---------------------------------------------------------------------------


def _get_llm():
    """Get the initialized LLM, setting it up if needed."""
    if not form.SELECTED_MODEL or not getattr(form.SELECTED_MODEL, "llm", None):
        if form.SELECTED_MODEL:
            form.SELECTED_MODEL.setup()
    return form.SELECTED_MODEL.llm


def build_mission_sub_agent(user_id: str):
    """Build a compiled ReAct sub-agent for mission operations."""
    from workflows.agent_tools.mission_tools import build_mission_tools

    tools = build_mission_tools(user_id)
    agent = create_react_agent(
        model=_get_llm(),
        tools=tools,
        prompt=_MISSION_AGENT_PROMPT,
    )
    log_info(f"[SubAgent] Built mission agent with {len(tools)} tools")
    return agent


def build_note_sub_agent(user_id: str):
    """Build a compiled ReAct sub-agent for note operations."""
    from workflows.agent_tools.note_tools import build_note_tools

    tools = build_note_tools(user_id)
    agent = create_react_agent(
        model=_get_llm(),
        tools=tools,
        prompt=_NOTE_AGENT_PROMPT,
    )
    log_info(f"[SubAgent] Built note agent with {len(tools)} tools")
    return agent


def build_sql_sub_agent(user_id: str):
    """Build a compiled ReAct sub-agent for SQL operations."""
    from workflows.agent_tools.sql_tools import build_sql_tools

    tools = build_sql_tools(user_id)
    agent = create_react_agent(
        model=_get_llm(),
        tools=tools,
        prompt=_SQL_AGENT_PROMPT,
    )
    log_info(f"[SubAgent] Built SQL agent with {len(tools)} tools")
    return agent


def build_flashcard_sub_agent(user_id: str):
    """Build a compiled ReAct sub-agent for flashcard operations."""
    from workflows.agent_tools.flashcard_tools import build_flashcard_tools

    tools = build_flashcard_tools(user_id)
    agent = create_react_agent(
        model=_get_llm(),
        tools=tools,
        prompt=_FLASHCARD_AGENT_PROMPT,
    )
    log_info(f"[SubAgent] Built flashcard agent with {len(tools)} tools")
    return agent


def build_automation_sub_agent(user_id: str):
    """Build a compiled ReAct sub-agent for automation/scheduled task operations."""
    from workflows.agent_tools.automation_tools import build_automation_tools

    tools = build_automation_tools(user_id)
    agent = create_react_agent(
        model=_get_llm(),
        tools=tools,
        prompt=_AUTOMATION_AGENT_PROMPT,
    )
    log_info(f"[SubAgent] Built automation agent with {len(tools)} tools")
    return agent


def build_audio_sub_agent(user_id: str):
    """Build a compiled ReAct sub-agent for audio overview operations."""
    from workflows.agent_tools.audio_tools import build_audio_tools

    tools = build_audio_tools(user_id)
    agent = create_react_agent(
        model=_get_llm(),
        tools=tools,
        prompt=_AUDIO_AGENT_PROMPT,
    )
    log_info(f"[SubAgent] Built audio agent with {len(tools)} tools")
    return agent


def build_os_sub_agent(user_id: str):
    """Build a compiled ReAct sub-agent for OS control operations."""
    from workflows.agent_tools.os_control_tools import build_os_control_tools

    tools = build_os_control_tools(user_id)
    agent = create_react_agent(
        model=_get_llm(),
        tools=tools,
        prompt=_OS_AGENT_PROMPT,
    )
    log_info(f"[SubAgent] Built OS agent with {len(tools)} tools")
    return agent
