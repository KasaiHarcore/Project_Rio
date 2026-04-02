"""ReAct tools for long-term memory operations.

Wraps the PostgresStore-based memory system for store/recall/forget.
"""

from __future__ import annotations

import json
from typing import Optional
from uuid import uuid4

from langchain_core.tools import tool

from utils.log import log_info


def build_memory_tools(user_id: str, store=None) -> list:
    """Build memory tools with user_id and store baked into closures.

    Args:
        user_id: User identifier for memory scoping.
        store: PostgresStore instance from memory_store_context().
               If None, memory tools are no-ops that return helpful messages.
    """

    @tool
    def recall_memories(query: str, limit: int = 5) -> str:
        """Search long-term memory for relevant facts about the user.

        Use this when the user asks "what do you know about me?",
        "do you remember...", or when past context would help.

        Args:
            query: What to search for in memory.
            limit: Maximum number of memories to return.

        Returns:
            JSON array of matching memories with text, score, and type.
        """
        if store is None:
            return json.dumps({"memories": [], "message": "Memory store not available"})
        from workflows.memory_store import search_memories

        memories = search_memories(store, user_id=user_id, query=query, limit=limit)
        return json.dumps(memories, default=str)

    @tool
    def store_memory(text: str, memory_type: str = "semantic") -> str:
        """Store a fact in long-term memory for future recall.

        Use this when the user explicitly says "remember that...",
        "keep in mind...", or shares important personal information.

        Args:
            text: The fact or information to remember.
            memory_type: Type of memory — "semantic" (facts), "episodic" (experiences),
                         or "procedural" (how-to knowledge).

        Returns:
            JSON confirmation of storage.
        """
        if store is None:
            return json.dumps({"success": False, "message": "Memory store not available"})
        from workflows.memory_store import store_memory as _store

        memory_key = f"explicit_{uuid4().hex[:12]}"
        _store(
            store,
            user_id=user_id,
            memory_key=memory_key,
            text=text,
            memory_type=memory_type,
            metadata={"source": "user_explicit"},
        )
        log_info(f"[memory] Stored explicit memory for user {user_id}: {text[:80]}")
        return json.dumps({"success": True, "message": f"Remembered: {text[:100]}"})

    @tool
    def forget_memory(query: str) -> str:
        """Forget/delete memories matching a topic.

        Use this when the user says "forget that...", "don't remember...",
        or wants to remove stored information.

        Args:
            query: Description of what to forget. Searches existing memories
                   and deletes the best match.

        Returns:
            JSON confirmation of deletion or message if nothing found.
        """
        if store is None:
            return json.dumps({"success": False, "message": "Memory store not available"})
        from workflows.memory_store import search_memories, delete_memory

        matches = search_memories(store, user_id=user_id, query=query, limit=3)
        if not matches:
            return json.dumps({"success": False, "message": "No matching memories found"})

        deleted_count = 0
        for mem in matches:
            key = mem.get("key") or mem.get("memory_key")
            if key:
                if delete_memory(store, user_id=user_id, memory_key=key):
                    deleted_count += 1

        if deleted_count:
            return json.dumps({
                "success": True,
                "message": f"Forgot {deleted_count} memory(ies) related to: {query[:80]}",
            })
        return json.dumps({"success": False, "message": "Found matches but could not delete"})

    return [recall_memories, store_memory, forget_memory]
