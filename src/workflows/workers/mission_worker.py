"""
Mission Worker — Creates and interacts with persistent missions.

This worker is triggered by the supervisor when the conversation
involves mission management:

1. **Create** — Extract new missions from conversation context
2. **Interact** — Toggle step completion or mark missions done on existing missions

The worker first uses an LLM to classify the user's intent, then either
extracts new missions or performs actions on existing ones via MissionTool.
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

INTENT_CLASSIFICATION_PROMPT = """You are the Mission classifier.

Sensei said: "{question}"

Recent conversation:
{history}

Active missions:
{missions_summary}

Pick ONE intent:
- CREATE  → Sensei wants to add/plan new tasks or goals.
- TOGGLE_STEP → Sensei wants to mark a specific step done/undone.
- COMPLETE_MISSION → Sensei wants to finish an entire mission.
- QUERY → Sensei is *asking about* their missions (count, status, progress, deadlines, lists, etc.).

Return ONLY JSON:
{{"intent":"…","reasoning":"one sentence","target_mission_id":"uuid|null","target_mission_title":"title|null","step_index":int_or_null,"step_text":"text|null"}}

Decision rules (in priority order):
1. Explicit check/uncheck words ("mark step", "tick off", "finished step") → TOGGLE_STEP
2. Whole-mission done words ("complete mission", "I'm done with", "mark … as done") → COMPLETE_MISSION
3. Question-shaped or info-seeking ("how many", "show me", "what's due", "status of", "am I on track", "which", "list", "any overdue", "what should I") → QUERY
4. Everything else (implied or explicit new work) → CREATE"""


QUERY_FILTER_PROMPT = """Today is {today}.

Sensei's question: "{question}"

Active missions context:
{missions_summary}

Your ONLY job: translate the question into DB query filters.

Return ONLY a JSON object with these fields (set unused fields to null):
{{"status": "active|completed|draft|archived|all" or null,
  "deadline_before": "ISO 8601" or null,
  "deadline_after": "ISO 8601" or null,
  "completed_since": "ISO 8601" or null,
  "category": "string" or null,
  "priority": "low|normal|critical" or null,
  "tag": "string" or null,
  "overdue_only": bool or null,
  "urgent_only": bool or null,
  "target_mission_title": "string" or null}}

Guidelines:
- Compute all dates relative to today ({today}).
- "this month" → deadline_after = first day of month, deadline_before = last day of month.
- "this week" → deadline_after = most recent Monday, deadline_before = coming Sunday 23:59.
- "last week/month" → use completed_since for the period start, status = "completed".
- "end of year" → deadline_before = {today[:4]}-12-31T23:59:59Z.
- "overdue" → overdue_only = true.
- "urgent" / "what should I do next" / "due soonest" → urgent_only = true.
- "study tasks" / "coding missions" → infer tag or category.
- "about mission X" / "status of X" → set target_mission_title = "X", status = "all".
- Questions about counts/totals/progress/hours/steps → status = "all" (aggregation is auto-computed).
- Default status to "active" when asking about upcoming work; "all" when asking for overview/stats."""


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

## Output Format — STRICT FIELD CONSTRAINTS
Return a JSON array of mission objects. Each mission has:
- "title": string — short, action-oriented title (1-500 chars, REQUIRED)
- "description": string | null — 1-3 sentence explanation (max 2000 chars)
- "priority": "low" | "normal" | "critical" — MUST be one of these three exact values
- "tags": array of strings — max 8 tags, each max 50 chars (e.g. ["study", "backend"])
- "steps": array of objects — max 15 steps, each: {{"text": string (max 300 chars), "done": false}}
- "deadline": string | null — ISO 8601 date/datetime (e.g. "2026-02-20" or "2026-02-20T18:00:00Z"). null if no clear deadline.
- "estimated_minutes": integer | null — must be between 1 and 14400 (10 days). null if hard to estimate.
- "meet_url": string | null — a meeting URL if provided (max 500 chars). null if not applicable.
- "category": string | null — single category label, max 100 chars (e.g. "Study", "Project", "DevOps")

Example:
[{{"title": "Build a REST API for user management", "description": "Create CRUD endpoints for user registration and profile management.", "priority": "normal", "tags": ["backend", "api"], "deadline": "2026-02-28T23:59:00Z", "estimated_minutes": 480, "meet_url": null, "category": "Project", "steps": [{{"text": "Design database schema", "done": false}}, {{"text": "Implement endpoints", "done": false}}]}}]

Now analyze and extract missions:"""


# ── Worker ───────────────────────────────────────────────────────────────────

class MissionWorker(BaseWorker):
    """
    Worker that creates new missions or interacts with existing ones.

    Supported intents:
    - CREATE: extract missions from conversation (original behaviour)
    - TOGGLE_STEP: toggle a step's done status on an existing mission
    - COMPLETE_MISSION: mark an entire mission as completed
    """

    @property
    def worker_type(self) -> WorkerType:
        return WorkerType.MISSION

    @property
    def name(self) -> str:
        return "Mission Worker"

    @property
    def description(self) -> str:
        return (
            "Creates new missions or interacts with existing ones "
            "(toggle step completion, mark missions complete)."
        )

    @property
    def system_prompt(self) -> str:
        return (
            "I am the Mission module. I create new missions and manage "
            "existing ones (toggle steps, mark complete) for Sensei. "
            "I always return valid JSON. I never include commentary outside the JSON."
        )

    # ── Core execution ───────────────────────────────────────────────────────

    def _execute(self, state: AgentState) -> WorkerResult:
        question = state.get("original_question", "")
        context = state.get("gathered_context", "")
        user_id = state.get("user_id")

        # Fallback: some graph configurations store user_id inside metadata
        if not user_id:
            meta = state.get("metadata") or {}
            user_id = meta.get("user_id")

        log_info(f"Mission worker: user_id={user_id!r}, question={question[:80]!r}")

        history_text = self._recent_history(state, max_turns=8)
        if history_text:
            context = f"{history_text}\n\n{context}" if context else history_text

        if not question and not context:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error="No question or context to process.",
            )

        # ── Step 1: Load existing missions for context ───────────────────
        missions_summary = "(no missions loaded — user_id unavailable)"
        existing_missions: list = []
        if user_id:
            try:
                from infrastructure.tools.mission_tool import MissionTool
                tool = MissionTool()
                existing_missions = tool.list_active_missions(str(user_id), limit=20)
                log_info(f"Mission worker: loaded {len(existing_missions)} active mission(s) for user {user_id}")
                if existing_missions:
                    lines = []
                    for m in existing_missions:
                        steps_str = ""
                        if m.get("steps"):
                            steps_str = " | Steps: " + ", ".join(
                                f"[{'x' if s['done'] else ' '}] #{s['index']}: {s['text']}"
                                for s in m["steps"]
                            )
                        lines.append(
                            f"- [{m['id']}] \"{m['title']}\" "
                            f"(status={m['status']}, progress={m['progress']}%{steps_str})"
                        )
                    missions_summary = "\n".join(lines)
                else:
                    missions_summary = "(no active missions)"
            except Exception as exc:
                log_warning(f"Mission worker: failed to load existing missions: {exc}")
                missions_summary = "(failed to load missions)"

        # ── Step 2: Classify intent ──────────────────────────────────────
        intent_data = self._classify_intent(question, history_text or "", missions_summary)
        intent = intent_data.get("intent", "CREATE")
        log_info(f"Mission worker intent: {intent} — {intent_data.get('reasoning', '')}")

        # ── Step 3: Execute based on intent ──────────────────────────────
        uid_str = str(user_id) if user_id else None
        if intent == "TOGGLE_STEP":
            return self._handle_toggle_step(uid_str, intent_data, existing_missions)

        if intent == "COMPLETE_MISSION":
            return self._handle_complete_mission(uid_str, intent_data, existing_missions)

        if intent == "QUERY":
            return self._handle_query(uid_str, question, intent_data)

        # Default: CREATE
        return self._handle_create(question, context)

    # ── Intent classification ────────────────────────────────────────────

    def _classify_intent(
        self, question: str, history: str, missions_summary: str
    ) -> Dict[str, Any]:
        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            question=question,
            history=(history or "(no history)")[:3000],
            missions_summary=missions_summary[:4000],
        )
        raw = self._call_llm(user_prompt=prompt)
        return self._parse_json_object(raw) or {"intent": "CREATE"}

    # ── Handler: CREATE ──────────────────────────────────────────────────

    def _handle_create(self, question: str, context: str) -> WorkerResult:
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
                metadata={"action": "create", "mission_count": 0},
            )

        content = json.dumps(missions, ensure_ascii=False)
        log_info(f"Mission worker extracted {len(missions)} mission(s)")

        return WorkerResult(
            worker_type=self.worker_type,
            success=True,
            content=content,
            metadata={"action": "create", "mission_count": len(missions)},
        )

    # ── Handler: TOGGLE_STEP ─────────────────────────────────────────────

    def _handle_toggle_step(
        self,
        user_id: Optional[str],
        intent_data: Dict[str, Any],
        existing_missions: List[Dict[str, Any]],
    ) -> WorkerResult:
        if not user_id:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error="Cannot toggle step — user not identified.",
            )

        mission_id = intent_data.get("target_mission_id")
        step_index = intent_data.get("step_index")
        step_text = intent_data.get("step_text")
        mission_title = intent_data.get("target_mission_title")

        # Resolve mission by ID or title
        target = self._resolve_mission(mission_id, mission_title, existing_missions)
        if not target:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=f"Could not find mission matching '{mission_title or mission_id}'.",
            )

        # Resolve step index by index or text match
        resolved_index = self._resolve_step_index(target, step_index, step_text)
        if resolved_index is None:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=f"Could not find step matching '{step_text or step_index}' in mission '{target['title']}'.",
            )

        from infrastructure.tools.mission_tool import MissionTool
        tool = MissionTool()
        result = tool.toggle_step(str(user_id), target["id"], resolved_index)

        if not result:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=f"Failed to toggle step {resolved_index} on mission '{target['title']}'.",
            )

        content = json.dumps({
            "action": "toggle_step",
            "mission": result,
            "step_index": resolved_index,
        }, ensure_ascii=False)

        return WorkerResult(
            worker_type=self.worker_type,
            success=True,
            content=content,
            metadata={
                "action": "toggle_step",
                "mission_id": target["id"],
                "step_index": resolved_index,
            },
        )

    # ── Handler: COMPLETE_MISSION ────────────────────────────────────────

    def _handle_complete_mission(
        self,
        user_id: Optional[str],
        intent_data: Dict[str, Any],
        existing_missions: List[Dict[str, Any]],
    ) -> WorkerResult:
        if not user_id:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error="Cannot complete mission — user not identified.",
            )

        mission_id = intent_data.get("target_mission_id")
        mission_title = intent_data.get("target_mission_title")

        target = self._resolve_mission(mission_id, mission_title, existing_missions)
        if not target:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=f"Could not find mission matching '{mission_title or mission_id}'.",
            )

        from infrastructure.tools.mission_tool import MissionTool
        tool = MissionTool()
        result = tool.complete_mission(str(user_id), target["id"])

        if not result:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=f"Failed to complete mission '{target['title']}'.",
            )

        content = json.dumps({
            "action": "complete_mission",
            "mission": result,
        }, ensure_ascii=False)

        return WorkerResult(
            worker_type=self.worker_type,
            success=True,
            content=content,
            metadata={
                "action": "complete_mission",
                "mission_id": target["id"],
            },
        )

    # ── Handler: QUERY ───────────────────────────────────────────────────

    def _handle_query(
        self,
        user_id: Optional[str],
        question: str,
        intent_data: Dict[str, Any],
    ) -> WorkerResult:
        if not user_id:
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error="Cannot query missions — user not identified.",
            )

        filters = intent_data.get("query_filters") or {}

        try:
            from infrastructure.tools.mission_tool import MissionTool
            tool = MissionTool()
            data = tool.query_missions(
                user_id,
                status=filters.get("status"),
                deadline_before=filters.get("deadline_before"),
                deadline_after=filters.get("deadline_after"),
                category=filters.get("category"),
                priority=filters.get("priority"),
                overdue_only=bool(filters.get("overdue_only")),
                completed_since=filters.get("completed_since"),
                urgent_only=bool(filters.get("urgent_only")),
                tag=filters.get("tag"),
            )
        except Exception as e:
            log_warning(f"MissionTool.query_missions failed: {e}")
            return WorkerResult(
                worker_type=self.worker_type,
                success=False,
                content="",
                error=f"Failed to query missions: {e}",
            )

        content = json.dumps(data, ensure_ascii=False)
        log_info(
            f"Mission QUERY: stats={data['stats']}, matching={data['matching_count']}"
        )

        return WorkerResult(
            worker_type=self.worker_type,
            success=True,
            content=content,
            gathered_context=content,
            metadata={"action": "query"},
        )

    # ── Resolution helpers ───────────────────────────────────────────────

    def _resolve_mission(
        self,
        mission_id: Optional[str],
        mission_title: Optional[str],
        existing_missions: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Find a mission by ID or fuzzy title match."""
        if not existing_missions:
            return None

        if mission_id:
            for m in existing_missions:
                if m["id"] == mission_id:
                    return m

        if mission_title:
            title_lower = mission_title.lower()
            for m in existing_missions:
                if title_lower in m["title"].lower() or m["title"].lower() in title_lower:
                    return m

        return None

    def _resolve_step_index(
        self,
        mission: Dict[str, Any],
        step_index: Optional[int],
        step_text: Optional[str],
    ) -> Optional[int]:
        """Resolve a step index from explicit index or fuzzy text match."""
        steps = mission.get("steps", [])
        if not steps:
            return None

        if step_index is not None and isinstance(step_index, int):
            if 0 <= step_index < len(steps):
                return step_index

        if step_text:
            text_lower = step_text.lower()
            for s in steps:
                if text_lower in s.get("text", "").lower():
                    return s["index"]

        return None

    # ── Parsing helpers ────────────────────────────────────────────────────

    def _recent_history(self, state: AgentState, max_turns: int = 8) -> str:
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

    def _parse_json_object(self, raw: str) -> Optional[Dict[str, Any]]:
        """Extract the first JSON object from LLM output."""
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"```(?:json)?\s*", "", text)
            text = text.replace("```", "").strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group())
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _parse_missions(self, raw: str) -> List[Dict[str, Any]]:
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

            raw_est = item.get("estimated_minutes")
            if raw_est is not None:
                try:
                    est = int(raw_est)
                    if 1 <= est <= 14400:
                        mission["estimated_minutes"] = est
                except (ValueError, TypeError):
                    pass

            raw_cat = item.get("category")
            if raw_cat and isinstance(raw_cat, str):
                mission["category"] = raw_cat.strip()[:100] or None
            
            raw_meet_url = item.get("meet_url")
            if raw_meet_url and isinstance(raw_meet_url, str):
                mission["meet_url"] = raw_meet_url.strip()[:500] or None

            raw_tags = item.get("tags")
            if isinstance(raw_tags, list):
                for t in raw_tags[:8]:
                    tag = str(t).strip()[:50]
                    if tag:
                        mission["tags"].append(tag)

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
