"""
Mission Worker — Auto-extracts actionable missions from conversations.

This worker is triggered by the supervisor when the conversation
produces goal-oriented tasks, study plans, project milestones, or
action items that should be tracked as persistent missions.

The Mission Worker:
- Analyses the conversation to identify goals and tasks
- Structures findings as Mission objects with optional step checklists
- Returns structured JSON so the frontend can render them on the Mission Page
  and so the backend can persist them to the database

Unlike the Note Worker (session-scoped sidebar sticky notes), the Mission Worker
produces **persistent, trackable tasks** that live in the Mission Page and survive
across sessions.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from langchain_core.messages import BaseMessage

from workflows.workers.base import BaseWorker
from workflows.state import AgentState, WorkerResult, WorkerType
from utils.log import log_debug, log_info, log_warning

if TYPE_CHECKING:
    from core.settings import AgentConfig


# ── Prompts ──────────────────────────────────────────────────────────────────

MISSION_EXTRACTION_PROMPT = """I am the Mission-planning module. I will analyze the conversation and extract actionable missions (tasks / goals) that Sensei should track.

## Sensei's Question / Request
{question}

## Context (worker results, conversation so far)
{context}

## Instructions
1. Identify concrete, trackable goals or tasks from the conversation.
2. Each mission should be a meaningful unit of work — not trivial one-liners.
3. If a goal has clear sub-steps, include them as a checklist.
4. Assign an appropriate priority: "low", "normal", or "critical".
5. Add short tag labels that categorize the mission (e.g. "study", "project", "backend").
6. Estimate a reasonable deadline (ISO 8601 date) based on scope and complexity.
7. Estimate how long the mission will take in minutes (estimated_minutes).
8. Assign a single category label that groups the mission (e.g. "Study", "Project", "Career", "Health").
9. Produce 1-3 missions maximum. Quality over quantity.
10. If there is nothing worth tracking as a mission, return an empty array.

## Output Format
Return a JSON array of mission objects. Each mission has:
- "title": string — short, action-oriented title (max 80 chars)
- "description": string — 1-3 sentence explanation of the goal
- "priority": "low" | "normal" | "critical"
- "tags": array of short string labels
- "steps": array of {{"text": string, "done": false}} — optional checklist of sub-tasks
- "deadline": string | null — ISO 8601 date or datetime (e.g. "2026-02-20" or "2026-02-20T18:00:00Z"). Estimate a reasonable due date based on scope. null if no clear deadline.
- "estimated_minutes": number | null — estimated total time in minutes (e.g. 120 for ~2 hours). null if hard to estimate.
- "meet_url": string | null — a meeting URL if provided (e.g. "https://meet.google.com/abc-defg-hij"). null if not provided.
- "category": string | null — single category label (e.g. "Study", "Project", "DevOps")

Example:
[{{"title": "Build a REST API for user management", "description": "Create CRUD endpoints.", "priority": "normal", "tags": ["backend"], "deadline": "2026-02-28T23:59:00Z", "estimated_minutes": 480, "meet_url": "https://meet.google.com/abc", "category": "Project", "steps": []}}]

Now analyze and extract missions:"""


# ── Worker ───────────────────────────────────────────────────────────────────

class MissionWorker(BaseWorker):
    """
    Worker that extracts trackable missions and goals from the conversation.

    The supervisor delegates here when the interaction produces goals,
    project tasks, or study plans that should be persisted as missions
    on the Mission Page.
    """

    @property
    def worker_type(self) -> WorkerType:
        return WorkerType.MISSION

    @property
    def name(self) -> str:
        return "Mission Worker"

    @property
    def description(self) -> str:
        return "Extracts actionable missions, goals, and task plans from the conversation."

    @property
    def system_prompt(self) -> str:
        return (
            "I am the Mission-planning module. I identify goals and "
            "actionable tasks from conversations to help Sensei track progress. "
            "I always return valid JSON. I never include commentary outside the JSON array."
        )

    # ── Core execution ───────────────────────────────────────────────────────

    def _execute(self, state: AgentState) -> WorkerResult:
        """Run the mission extraction."""
        question = state.get("original_question", "")
        context = state.get("gathered_context", "")

        # Also include recent message history for richer context
        history_text = self._recent_history(state, max_turns=8)
        if history_text:
            context = f"{history_text}\n\n{context}" if context else history_text

        if not question and not context:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error="No question or context to extract missions from.",
            )

        prompt = MISSION_EXTRACTION_PROMPT.format(
            question=question,
            context=(context or "(no additional context)")[:6000],
        )

        raw = self._call_llm(user_prompt=prompt)
        missions = self._parse_missions(raw)

        if not missions:
            return WorkerResult(
                worker_type=self.worker_type,
                success=True,
                content="[]",
                metadata={"mission_count": 0},
            )

        content = json.dumps(missions, ensure_ascii=False)
        log_info(f"Mission worker extracted {len(missions)} mission(s)")

        return WorkerResult(
            worker_type=self.worker_type,
            success=True,
            content=content,
            metadata={"mission_count": len(missions)},
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _recent_history(state: AgentState, max_turns: int = 8) -> str:
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
    def _parse_missions(raw: str) -> List[Dict[str, Any]]:
        """Parse the LLM output into a list of mission dicts.

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
            log_warning(f"Mission worker: could not find JSON array in LLM output ({text[:200]})")
            return []

        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError as exc:
            log_warning(f"Mission worker: JSON parse error: {exc}")
            return []

        if not isinstance(parsed, list):
            return []

        # Validate & clean each mission
        VALID_PRIORITIES = {"low", "normal", "critical"}
        missions: List[Dict[str, Any]] = []

        for item in parsed[:3]:  # hard-cap at 3 missions per invocation
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "")).strip()
            if not title:
                continue

            mission: Dict[str, Any] = {
                "title": title[:500],
                "description": str(item.get("description", "")).strip()[:2000] or None,
                "priority": (
                    item.get("priority", "normal")
                    if item.get("priority") in VALID_PRIORITIES
                    else "normal"
                ),
                "tags": [],
                "steps": [],
                "deadline": item.get("deadline") if item.get("deadline") else None,
                "estimated_minutes": None,
                "meet_url": None,
                "category": None,
            }

            # Parse estimated_minutes
            raw_est = item.get("estimated_minutes")
            if raw_est is not None:
                try:
                    est = int(raw_est)
                    if 1 <= est <= 14400:
                        mission["estimated_minutes"] = est
                except (ValueError, TypeError):
                    pass

            # Parse category
            raw_cat = item.get("category")
            if raw_cat and isinstance(raw_cat, str):
                mission["category"] = raw_cat.strip()[:100] or None
            
            # Parse meet_url
            raw_meet_url = item.get("meet_url")
            if raw_meet_url and isinstance(raw_meet_url, str):
                mission["meet_url"] = raw_meet_url.strip()[:500] or None

            # Parse tags
            raw_tags = item.get("tags")
            if isinstance(raw_tags, list):
                for t in raw_tags[:8]:
                    tag = str(t).strip()[:50]
                    if tag:
                        mission["tags"].append(tag)

            # Parse steps
            raw_steps = item.get("steps")
            if isinstance(raw_steps, list):
                for s in raw_steps[:15]:  # hard-cap at 15 steps per mission
                    if isinstance(s, dict) and s.get("text"):
                        mission["steps"].append({
                            "text": str(s["text"]).strip()[:300],
                            "done": bool(s.get("done", False)),
                        })
                    elif isinstance(s, str) and s.strip():
                        mission["steps"].append({"text": s.strip()[:300], "done": False})

            missions.append(mission)

        return missions
