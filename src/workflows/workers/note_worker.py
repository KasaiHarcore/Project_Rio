"""
Note Worker - Extracts Important Notes & TODO Steps.

This worker is triggered by the supervisor when the conversation
produces actionable insights, study plans, important notes, or
TODO items that should be surfaced in the sidebar.

The Note Worker:
- Analyses the conversation to extract key takeaways
- Structures findings as notes with optional TODO checklists
- Returns structured JSON so the frontend can render sticky notes

Unlike the Memory Worker (which stores long-term facts), the Note Worker
produces **session-scoped, visible artefacts** that appear in the chat
sidebar's "Notes" section.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from langchain_core.messages import BaseMessage, HumanMessage

from workflows.workers.base import BaseWorker
from workflows.state import AgentState, WorkerResult, WorkerType
from utils.log import log_debug, log_info, log_warning

if TYPE_CHECKING:
    from core.settings import AgentConfig


# ── Prompts ──────────────────────────────────────────────────────────────────

NOTE_EXTRACTION_PROMPT = """I am the Note-taking module. I will analyze the conversation and extract important notes or actionable TODO items to help Sensei stay organized.

## Sensei's Question / Request
{question}

## Context (worker results, conversation so far)
{context}

## Instructions
1. Extract the most important takeaways, insights, or action items.
2. If the content suggests a step-by-step plan, study roadmap, or action list, structure it as TODO items.
3. Keep each note concise (1-3 sentences for plain notes, short phrases for TODOs).
4. Produce 1-3 notes maximum. Quality over quantity.
5. If there is nothing noteworthy, return an empty array.

## Output Format
Return a JSON array of note objects. Each note has:
- "content": string — the note text (also used as a summary for TODO notes)
- "todos": array of {{"text": string, "done": false}} — optional, include ONLY if the note is a checklist/plan

Example outputs:

Plain note:
[{{"content": "The CAP theorem states that a distributed system can only guarantee two of: Consistency, Availability, Partition tolerance."}}]

TODO note:
[{{"content": "Study plan for React hooks", "todos": [{{"text": "Read useState documentation", "done": false}}, {{"text": "Practice useEffect cleanup patterns", "done": false}}, {{"text": "Build a custom hook for form validation", "done": false}}]}}]

Mixed:
[{{"content": "PostgreSQL uses MVCC for concurrency control — each transaction sees a snapshot."}}, {{"content": "Database optimization checklist", "todos": [{{"text": "Add indexes on frequently queried columns", "done": false}}, {{"text": "Run EXPLAIN ANALYZE on slow queries", "done": false}}]}}]

Now analyze and extract notes:"""


# ── Worker ───────────────────────────────────────────────────────────────────

class NoteWorker(BaseWorker):
    """
    Worker that extracts important notes and TODO items from the conversation.

    The supervisor delegates here when the interaction produces content
    worth surfacing as a sticky note in the chat sidebar.
    """

    @property
    def worker_type(self) -> WorkerType:
        return WorkerType.NOTE

    @property
    def name(self) -> str:
        return "Note Worker"

    @property
    def description(self) -> str:
        return "Extracts important notes, key takeaways, and TODO action items from the conversation."

    @property
    def system_prompt(self) -> str:
        return (
            "I am the Note-taking module. I extract key insights and "
            "actionable steps from conversations to help Sensei stay organized. "
            "I always return valid JSON. I never include commentary outside the JSON array."
        )

    # ── Core execution ───────────────────────────────────────────────────────

    def _execute(self, state: AgentState) -> WorkerResult:
        """Run the note extraction."""
        question = state.get("original_question", "")
        context = state.get("gathered_context", "")

        # Also include recent message history for richer context
        history_text = self._recent_history(state, max_turns=6)
        if history_text:
            context = f"{history_text}\n\n{context}" if context else history_text

        if not question and not context:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error="No question or context to extract notes from.",
            )

        prompt = NOTE_EXTRACTION_PROMPT.format(
            question=question,
            context=(context or "(no additional context)")[:4000],
        )

        raw = self._call_llm(user_prompt=prompt)
        notes = self._parse_notes(raw)

        if not notes:
            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content="[]",
                metadata={"note_count": 0},
            )

        # Return the structured notes as JSON string
        content = json.dumps(notes, ensure_ascii=False)
        log_info(f"Note worker extracted {len(notes)} note(s)")

        return WorkerResult(
            worker_type=self.worker_type,
            success=True,
            content=content,
            metadata={"note_count": len(notes)},
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _recent_history(state: AgentState, max_turns: int = 6) -> str:
        """Build a short text summary of recent conversation turns."""
        msgs: list[BaseMessage] = list(state.get("messages") or [])
        if not msgs:
            return ""

        tail = msgs[-max_turns:] if len(msgs) > max_turns else msgs
        parts: list[str] = []
        for m in tail:
            role = getattr(m, "type", "unknown")
            content = str(m.content or "")[:500]
            parts.append(f"[{role}] {content}")
        return "\n".join(parts)

    @staticmethod
    def _parse_notes(raw: str) -> List[Dict[str, Any]]:
        """Parse the LLM output into a list of note dicts.

        Handles markdown code fences and minor formatting issues.
        """
        text = raw.strip()

        # Strip markdown code fences
        if text.startswith("```"):
            text = re.sub(r"```(?:json)?\s*", "", text)
            text = text.replace("```", "").strip()

        # Find the JSON array
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            log_warning(f"Note worker: could not find JSON array in LLM output ({text[:200]})")
            return []

        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError as exc:
            log_warning(f"Note worker: JSON parse error: {exc}")
            return []

        if not isinstance(parsed, list):
            return []

        # Validate & clean each note
        notes: List[Dict[str, Any]] = []
        for item in parsed[:3]:  # hard-cap at 3 notes per invocation
            if not isinstance(item, dict):
                continue
            content = str(item.get("content", "")).strip()
            if not content:
                continue

            note: Dict[str, Any] = {"content": content[:500]}

            todos_raw = item.get("todos")
            if isinstance(todos_raw, list) and todos_raw:
                todos = []
                for t in todos_raw[:10]:  # hard-cap at 10 TODO items per note
                    if isinstance(t, dict) and t.get("text"):
                        todos.append({
                            "text": str(t["text"]).strip()[:200],
                            "done": bool(t.get("done", False)),
                        })
                    elif isinstance(t, str) and t.strip():
                        todos.append({"text": t.strip()[:200], "done": False})
                if todos:
                    note["todos"] = todos

            notes.append(note)

        return notes
