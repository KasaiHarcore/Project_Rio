"""Delegation tools for the ReAct supervisor.

Each delegation tool invokes a specialized ReAct sub-agent synchronously,
passing the supervisor's instruction as a HumanMessage, and returns the
sub-agent's final text response.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from utils.log import log_info, log_warning


def _invoke_sub_agent(agent, instruction: str) -> str:
    """Invoke a compiled ReAct sub-agent and extract its final text response."""
    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content=instruction)]},
        )
        # Extract the last AI message content
        messages = result.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                return msg.content
        return "Sub-agent completed but produced no text response."
    except Exception as e:
        log_warning(f"[Delegation] Sub-agent failed: {e}")
        return f"Sub-agent error: {e}"


def build_delegation_tools(user_id: str, user_role: str) -> list:
    """Build delegation tools that invoke domain-specific sub-agents.

    Sub-agents are lazily constructed on first call to avoid building
    unused agents. Admin-only agents (SQL, OS) are only included for admin users.

    Args:
        user_id: Authenticated user identifier.
        user_role: User role — "user" or "admin".

    Returns:
        List of delegation @tool functions.
    """

    # Lazy sub-agent cache — built on first invocation
    _cache: Dict[str, Any] = {}

    def _get_agent(name: str):
        if name not in _cache:
            from workflows.tools.sub_agents import (
                build_mission_sub_agent,
                build_note_sub_agent,
                build_flashcard_sub_agent,
                build_automation_sub_agent,
                build_audio_sub_agent,
                build_sql_sub_agent,
                build_os_sub_agent,
            )

            builders = {
                "mission": build_mission_sub_agent,
                "note": build_note_sub_agent,
                "flashcard": build_flashcard_sub_agent,
                "automation": build_automation_sub_agent,
                "audio": build_audio_sub_agent,
                "sql": build_sql_sub_agent,
                "os": build_os_sub_agent,
            }
            _cache[name] = builders[name](user_id)
        return _cache[name]

    # ── Domain delegation tools ──

    @tool
    def delegate_mission_task(instruction: str) -> str:
        """Delegate a mission/goal/task operation to the Mission Agent.

        Use this for ANY mission-related request: creating missions, toggling steps,
        completing missions, updating details, querying progress, or deleting missions.

        The Mission Agent has tools to list, create, update, toggle, complete,
        and delete missions. It will see real mission data with actual IDs and steps.

        Args:
            instruction: Clear description of what to do with missions.
                         Include any relevant details from the conversation
                         (e.g. "toggle step 2 of the Gym Routine mission").

        Returns:
            The Mission Agent's response describing what it did and the result.
        """
        log_info(f"[Delegation] → Mission Agent: {instruction[:100]}")
        return _invoke_sub_agent(_get_agent("mission"), instruction)

    @tool
    def delegate_note_task(instruction: str) -> str:
        """Delegate a note operation to the Note Agent.

        Use this for ANY note-related request: creating notes, searching notes,
        updating content, managing collections, viewing the note graph, or deleting notes.

        The Note Agent has tools to search, read, create, update, delete notes,
        manage collections, view graph relationships, and toggle todos.

        Args:
            instruction: Clear description of what to do with notes.
                         Include relevant context (e.g. "create a note titled
                         'React Hooks Summary' with content about useState and useEffect").

        Returns:
            The Note Agent's response describing what it did and the result.
        """
        log_info(f"[Delegation] → Note Agent: {instruction[:100]}")
        return _invoke_sub_agent(_get_agent("note"), instruction)

    @tool
    def delegate_flashcard_task(instruction: str) -> str:
        """Delegate a flashcard/study-card operation to the Flashcard Agent.

        Use this for ANY flashcard-related request: creating decks, generating
        flashcards from notes, reviewing cards, listing due cards, study stats,
        or when the user wants to study, quiz themselves, or make flashcards.

        Args:
            instruction: Clear description of what to do with flashcards.
                         Include any relevant details (note IDs, deck names,
                         card content, etc.).

        Returns:
            The Flashcard Agent's response describing what it did.
        """
        log_info(f"[Delegation] → Flashcard Agent: {instruction[:100]}")
        return _invoke_sub_agent(_get_agent("flashcard"), instruction)

    @tool
    def delegate_automation_task(instruction: str) -> str:
        """Delegate a scheduled automation operation to the Automation Agent.

        Use this when the user wants to: set up recurring tasks, create reminders,
        schedule daily/weekly agent actions, enable/disable automations, run an
        automation manually, or manage their scheduled tasks.

        Examples: "remind me every morning to review flashcards",
        "set up a weekly summary of my notes", "pause my daily automation",
        "run my study reminder now".

        Args:
            instruction: Clear description of what to do with automations.
                         Include schedule details, what the agent should do,
                         and any specific automation IDs if updating/deleting.

        Returns:
            The Automation Agent's response describing what it did.
        """
        log_info(f"[Delegation] → Automation Agent: {instruction[:100]}")
        return _invoke_sub_agent(_get_agent("automation"), instruction)

    @tool
    def delegate_audio_task(instruction: str) -> str:
        """Delegate an audio overview/podcast generation to the Audio Agent.

        Use this when the user wants to: generate audio from their notes,
        create a podcast/lecture/summary of study materials, listen to their
        notes, or check the status of audio generation.

        Examples: "make an audio summary of my biology notes",
        "create a podcast from my last 3 notes", "generate a lecture
        about machine learning from my notes".

        Args:
            instruction: Clear description of what audio to generate.
                         Include source note IDs if known, desired format
                         (summary/dialogue/lecture), and any title preference.

        Returns:
            The Audio Agent's response describing what it started.
        """
        log_info(f"[Delegation] → Audio Agent: {instruction[:100]}")
        return _invoke_sub_agent(_get_agent("audio"), instruction)

    tools = [delegate_mission_task, delegate_note_task, delegate_flashcard_task,
             delegate_automation_task, delegate_audio_task]

    # ── Admin-only delegation tools ──

    if user_role == "admin":

        @tool
        def delegate_sql_task(instruction: str) -> str:
            """Delegate a database query to the SQL Agent. ADMIN ONLY.

            Use this for ANY database-related request: querying data, describing
            schema, or executing SQL. Write operations require user approval.

            The SQL Agent has tools to describe the schema, get table info,
            and execute SQL queries with safety classification.

            Args:
                instruction: Clear description of the database question or operation.
                             E.g. "show me the 10 most recent users" or
                             "count how many active threads exist".

            Returns:
                The SQL Agent's response with query results or schema information.
            """
            log_info(f"[Delegation] → SQL Agent: {instruction[:100]}")
            return _invoke_sub_agent(_get_agent("sql"), instruction)

        @tool
        def delegate_os_task(instruction: str) -> str:
            """Delegate an OS command to the OS Control Agent. ADMIN ONLY.

            Use this for shell commands, system diagnostics, or file operations.
            High-risk commands require user approval.

            The OS Agent has tools to execute shell commands with risk classification.

            Args:
                instruction: Clear description of the OS operation.
                             E.g. "check disk usage" or "list files in /tmp".

            Returns:
                The OS Agent's response with command output and status.
            """
            log_info(f"[Delegation] → OS Agent: {instruction[:100]}")
            return _invoke_sub_agent(_get_agent("os"), instruction)

        tools.extend([delegate_sql_task, delegate_os_task])

    return tools
