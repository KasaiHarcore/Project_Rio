from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from utils.log import log_info, log_warning
from workflows.state import WorkerResult, WorkerType

if TYPE_CHECKING:
    from core.settings import AgentConfig


# ═══════════════════════════════════════════════════════════════════════════
# State
# ═══════════════════════════════════════════════════════════════════════════

class MissionState(TypedDict, total=False):
    """Internal state for the mission subgraph."""

    # ── Inputs (set once by the entry adapter) ───────────────────
    question: str
    context: str           # gathered_context from parent
    history: str           # recent chat turns
    user_id: Optional[str]

    # ── Intermediate ─────────────────────────────────────────────
    missions_summary: str          # human-readable summary for prompts
    existing_missions: List[Dict[str, Any]]  # raw dicts from DB

    intent: str                    # CREATE | TOGGLE_STEP | COMPLETE_MISSION | QUERY
    intent_data: Dict[str, Any]    # full JSON from classifier

    query_filters: Dict[str, Any]  # populated only for QUERY

    # ── Output ───────────────────────────────────────────────────
    result: Optional[Dict[str, Any]]  # serialisable WorkerResult fields


# ═══════════════════════════════════════════════════════════════════════════
# Prompts
# ═══════════════════════════════════════════════════════════════════════════

INTENT_PROMPT = """You are the Mission classifier.

Sensei said: "{question}"

Recent conversation:
{history}

Active missions:
{missions_summary}

Pick ONE intent:
- CREATE  → Sensei wants to add/plan new tasks or goals.
- TOGGLE_STEP → Sensei wants to mark a specific step done/undone.
- COMPLETE_MISSION → Sensei wants to finish an entire mission.
- UPDATE → Sensei wants to modify an existing mission (rename, change deadline, priority, add/remove steps, etc.).
- DELETE → Sensei wants to remove/delete an existing mission entirely.
- QUERY → Sensei is *asking about* their missions (count, status, progress, deadlines, lists, etc.).

Return ONLY JSON:
{{"intent":"…","reasoning":"one sentence","target_mission_id":"uuid|null","target_mission_title":"title|null","step_index":int_or_null,"step_text":"text|null"}}

Decision rules (in priority order):
1. Explicit check/uncheck words ("mark step", "tick off", "finished step") → TOGGLE_STEP
2. Whole-mission done words ("complete mission", "I'm done with", "mark … as done") → COMPLETE_MISSION
3. Delete/remove mission words ("delete mission", "remove mission", "cancel mission", "get rid of") → DELETE
4. Modify/change words targeting an existing mission ("change", "update", "modify", "rename", "move deadline", "set priority", "add a step to", "remove the step", "reschedule") → UPDATE
5. Question-shaped or info-seeking ("how many", "show me", "what's due", "status of", "am I on track", "which", "list", "any overdue", "what should I") → QUERY
6. Everything else (implied or explicit new work) → CREATE"""

FILTER_PROMPT = """Today is {today}.

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
- "end of year" → deadline_before = {year}-12-31T23:59:59Z.
- "overdue" → overdue_only = true.
- "urgent" / "what should I do next" / "due soonest" → urgent_only = true.
- "study tasks" / "coding missions" → infer tag or category.
- "about mission X" / "status of X" → set target_mission_title = "X", status = "all".
- Questions about counts/totals/progress/hours/steps → status = "all" (aggregation is auto-computed).
- Default status to "active" when asking about upcoming work; "all" when asking for overview/stats."""

EXTRACTION_PROMPT = """I am the Mission-planning module. I will analyze the conversation and extract actionable missions (tasks / goals) that Sensei should track.

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

UPDATE_PROMPT = """I am the Mission-update module. I extract what Sensei wants to change on an existing mission.

Sensei said: "{question}"

Active missions:
{missions_summary}

Identify:
1. Which mission to update (by title or ID).
2. Which fields to change and to what values.

Updatable fields:
- "title": string (max 500)
- "description": string (max 2000)
- "status": "active" | "draft" | "completed" | "archived"
- "priority": "low" | "normal" | "critical"
- "deadline": ISO 8601 datetime string or null to remove
- "scheduled_start": ISO 8601 datetime string or null
- "estimated_minutes": integer 1-14400 or null
- "category": string (max 100) or null
- "tags": array of strings (max 8 tags, each max 50 chars)
- "steps": array of {{"text": string, "done": bool}} — REPLACES all steps
- "meet_url": string or null
- "notes": string or null

Return ONLY JSON:
{{"target_mission_id": "uuid or null", "target_mission_title": "title or null", "updates": {{...only changed fields...}}}}

Rules:
- Only include fields that Sensei explicitly wants to change.
- "Move deadline to Friday" → {{"deadline": "2025-01-17T23:59:00Z"}}
- "Change priority to critical" → {{"priority": "critical"}}
- "Rename to X" → {{"title": "X"}}
- "Add a step: do Y" → include full steps array (existing + new).
- "Remove the step about Y" → include steps array without that step.
- Today is {today}.
"""


# ═══════════════════════════════════════════════════════════════════════════
# LLM helper (lightweight — avoids importing BaseWorker)
# ═══════════════════════════════════════════════════════════════════════════

def _call_llm(user_prompt: str, config: Optional["AgentConfig"] = None) -> str:
    """Invoke the LLM with a single user prompt. Returns raw text."""
    from infrastructure.llm import form
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

    system = (
        "I am the Mission module. I always return valid JSON. "
        "I never include commentary outside the JSON."
    )
    llm = form.SELECTED_MODEL.llm
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user_prompt)])
    if isinstance(resp, AIMessage):
        return str(resp.content)
    return str(resp)


# ═══════════════════════════════════════════════════════════════════════════
# JSON parsers
# ═══════════════════════════════════════════════════════════════════════════

def _strip_fences(text: str) -> str:
    """Remove markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"```(?:json)?\s*", "", text)
        text = text.replace("```", "").strip()
    return text


def _parse_json_object(raw: str) -> Optional[Dict[str, Any]]:
    text = _strip_fences(raw)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group())
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _parse_json_array(raw: str) -> List[Dict[str, Any]]:
    text = _strip_fences(raw)
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group())
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


# ═══════════════════════════════════════════════════════════════════════════
# Mission resolution helpers
# ═══════════════════════════════════════════════════════════════════════════

def _resolve_mission(
    mission_id: Optional[str],
    mission_title: Optional[str],
    existing_missions: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
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
    mission: Dict[str, Any],
    step_index: Optional[int],
    step_text: Optional[str],
) -> Optional[int]:
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


def _validate_missions(parsed: List) -> List[Dict[str, Any]]:
    """Clean and validate parsed mission dicts (max 3)."""
    VALID_PRIORITIES = {"low", "normal", "critical"}
    missions: List[Dict[str, Any]] = []

    for item in parsed[:3]:
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

        raw_meet = item.get("meet_url")
        if raw_meet and isinstance(raw_meet, str):
            mission["meet_url"] = raw_meet.strip()[:500] or None

        raw_tags = item.get("tags")
        if isinstance(raw_tags, list):
            for t in raw_tags[:8]:
                tag = str(t).strip()[:50]
                if tag:
                    mission["tags"].append(tag)

        raw_steps = item.get("steps")
        if isinstance(raw_steps, list):
            for s in raw_steps[:15]:
                if isinstance(s, dict) and s.get("text"):
                    mission["steps"].append({
                        "text": str(s["text"]).strip()[:300],
                        "done": bool(s.get("done", False)),
                    })
                elif isinstance(s, str) and s.strip():
                    mission["steps"].append({"text": s.strip()[:300], "done": False})

        missions.append(mission)
    return missions


def _make_result(
    success: bool,
    content: str = "",
    error: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    gathered_context: str = "",
) -> Dict[str, Any]:
    """Build the result dict that the exit adapter converts to WorkerResult."""
    return {
        "result": {
            "success": success,
            "content": content,
            "error": error,
            "metadata": metadata or {},
            "gathered_context": gathered_context,
        }
    }


# ═══════════════════════════════════════════════════════════════════════════
# Node 1 — load_missions
# ═══════════════════════════════════════════════════════════════════════════

def load_missions_node(state: MissionState) -> Dict[str, Any]:
    """Load the user's active missions from the DB. No LLM call."""
    user_id = state.get("user_id")
    if not user_id:
        return {
            "missions_summary": "(no missions loaded — user_id unavailable)",
            "existing_missions": [],
        }

    try:
        from infrastructure.tools.mission_tool import MissionTool
        tool = MissionTool()
        existing = tool.list_active_missions(str(user_id), limit=20)
        log_info(f"Mission subgraph: loaded {len(existing)} active mission(s)")
    except Exception as exc:
        log_warning(f"Mission subgraph: failed to load missions: {exc}")
        return {
            "missions_summary": "(failed to load missions)",
            "existing_missions": [],
        }

    if not existing:
        return {
            "missions_summary": "(no active missions)",
            "existing_missions": [],
        }

    lines: List[str] = []
    for m in existing:
        parts: List[str] = [f"status={m['status']}", f"progress={m['progress']}%"]
        if m.get("deadline"):
            parts.append(f"deadline={m['deadline']}")
        if m.get("priority"):
            parts.append(f"priority={m['priority']}")
        if m.get("category"):
            parts.append(f"category={m['category']}")
        if m.get("estimated_minutes"):
            parts.append(f"est={m['estimated_minutes']}min")
        if m.get("steps"):
            done = sum(1 for s in m["steps"] if s["done"])
            total = len(m["steps"])
            parts.append(f"steps={done}/{total}")
            steps_str = " | Steps: " + ", ".join(
                f"[{'x' if s['done'] else ' '}] #{s['index']}: {s['text']}"
                for s in m["steps"]
            )
            parts.append(steps_str)
        lines.append(
            f"- [{m['id']}] \"{m['title']}\" ({', '.join(parts)})"
        )

    return {
        "missions_summary": "\n".join(lines),
        "existing_missions": existing,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Node 2 — classify
# ═══════════════════════════════════════════════════════════════════════════

def classify_node(state: MissionState, config: Optional["AgentConfig"] = None) -> Dict[str, Any]:
    """LLM call #1: classify intent. Cheap & fast."""
    question = state.get("question", "")
    if not question:
        return {"intent": "CREATE", "intent_data": {"intent": "CREATE"}}

    prompt = INTENT_PROMPT.format(
        question=question,
        history=(state.get("history") or "(no history)")[:3000],
        missions_summary=(state.get("missions_summary") or "(none)")[:4000],
    )
    raw = _call_llm(prompt, config=config)
    data = _parse_json_object(raw) or {"intent": "CREATE"}
    intent = data.get("intent", "CREATE")
    log_info(f"Mission classify: {intent} — {data.get('reasoning', '')}")
    return {"intent": intent, "intent_data": data}


# ═══════════════════════════════════════════════════════════════════════════
# Node 3a — create_node
# ═══════════════════════════════════════════════════════════════════════════

def create_node(state: MissionState, config: Optional["AgentConfig"] = None) -> Dict[str, Any]:
    """Extract new missions from conversation via LLM."""
    question = state.get("question", "")
    context = state.get("context", "")

    prompt = EXTRACTION_PROMPT.format(
        question=question,
        context=(context or "(no additional context)")[:6000],
    )
    raw = _call_llm(prompt, config=config)
    parsed = _parse_json_array(raw)
    missions = _validate_missions(parsed)

    content = json.dumps(missions, ensure_ascii=False)
    log_info(f"Mission create: extracted {len(missions)} mission(s)")

    return _make_result(
        success=True,
        content=content,
        metadata={"action": "create", "mission_count": len(missions)},
    )


# ═══════════════════════════════════════════════════════════════════════════
# Node 3b — toggle_step_node
# ═══════════════════════════════════════════════════════════════════════════

def toggle_step_node(state: MissionState) -> Dict[str, Any]:
    """Toggle a step on an existing mission. Pure DB — no LLM."""
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="Cannot toggle step — user not identified.")

    data = state.get("intent_data") or {}
    existing = state.get("existing_missions") or []

    target = _resolve_mission(
        data.get("target_mission_id"),
        data.get("target_mission_title"),
        existing,
    )
    if not target:
        return _make_result(
            False,
            error=f"Could not find mission matching '{data.get('target_mission_title') or data.get('target_mission_id')}'.",
        )

    resolved_index = _resolve_step_index(target, data.get("step_index"), data.get("step_text"))
    if resolved_index is None:
        return _make_result(
            False,
            error=f"Could not find step matching '{data.get('step_text') or data.get('step_index')}' in mission '{target['title']}'.",
        )

    from infrastructure.tools.mission_tool import MissionTool
    result = MissionTool().toggle_step(str(user_id), target["id"], resolved_index)
    if not result:
        return _make_result(False, error=f"Failed to toggle step {resolved_index} on mission '{target['title']}'.")

    content = json.dumps({"action": "toggle_step", "mission": result, "step_index": resolved_index}, ensure_ascii=False)
    return _make_result(
        success=True,
        content=content,
        metadata={"action": "toggle_step", "mission_id": target["id"], "step_index": resolved_index},
    )


# ═══════════════════════════════════════════════════════════════════════════
# Node 3c — complete_mission_node
# ═══════════════════════════════════════════════════════════════════════════

def complete_mission_node(state: MissionState) -> Dict[str, Any]:
    """Mark an entire mission as completed. Pure DB — no LLM."""
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="Cannot complete mission — user not identified.")

    data = state.get("intent_data") or {}
    existing = state.get("existing_missions") or []

    target = _resolve_mission(
        data.get("target_mission_id"),
        data.get("target_mission_title"),
        existing,
    )
    if not target:
        return _make_result(
            False,
            error=f"Could not find mission matching '{data.get('target_mission_title') or data.get('target_mission_id')}'.",
        )

    from infrastructure.tools.mission_tool import MissionTool
    result = MissionTool().complete_mission(str(user_id), target["id"])
    if not result:
        return _make_result(False, error=f"Failed to complete mission '{target['title']}'.")

    content = json.dumps({"action": "complete_mission", "mission": result}, ensure_ascii=False)
    return _make_result(
        success=True,
        content=content,
        metadata={"action": "complete_mission", "mission_id": target["id"]},
    )


# ═══════════════════════════════════════════════════════════════════════════
# Node 3d — query_node  (LLM call #2: build filters → DB query)
# ═══════════════════════════════════════════════════════════════════════════

def query_node(state: MissionState, config: Optional["AgentConfig"] = None) -> Dict[str, Any]:
    """Two-step: LLM builds filters → MissionTool queries DB."""
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="Cannot query missions — user not identified.")

    question = state.get("question", "")
    missions_summary = state.get("missions_summary") or "(none)"

    # ── LLM call #2: extract filters ──
    today = date.today().isoformat()
    year = today[:4]
    prompt = FILTER_PROMPT.format(
        today=today,
        year=year,
        question=question,
        missions_summary=missions_summary[:4000],
    )
    raw = _call_llm(prompt, config=config)
    log_info(f"Mission query LLM raw: {raw[:500]}")
    filters = _parse_json_object(raw) or {}
    log_info(f"Mission query filters: {filters}")

    # ── DB query ──
    try:
        from infrastructure.tools.mission_tool import MissionTool
        data = MissionTool().query_missions(
            str(user_id),
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
        return _make_result(False, error=f"Failed to query missions: {e}")

    content = json.dumps(data, ensure_ascii=False)
    log_info(f"Mission QUERY: stats={data['stats']}, matching={data['matching_count']}")

    return _make_result(
        success=True,
        content=content,
        gathered_context=content,
        metadata={"action": "query"},
    )


# ═══════════════════════════════════════════════════════════════════════════
# Node 3e — update_mission_node  (LLM extracts changes → DB update)
# ═══════════════════════════════════════════════════════════════════════════

def update_mission_node(state: MissionState, config: Optional["AgentConfig"] = None) -> Dict[str, Any]:
    """LLM extracts field changes → resolve mission → apply update."""
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="Cannot update mission — user not identified.")

    question = state.get("question", "")
    missions_summary = state.get("missions_summary") or "(none)"
    existing = state.get("existing_missions") or []

    today = date.today().isoformat()
    prompt = UPDATE_PROMPT.format(
        question=question,
        missions_summary=missions_summary[:4000],
        today=today,
    )
    raw = _call_llm(prompt, config=config)
    log_info(f"Mission update LLM raw: {raw[:500]}")
    data = _parse_json_object(raw) or {}

    # ── Resolve target mission ──
    target = _resolve_mission(
        data.get("target_mission_id"),
        data.get("target_mission_title"),
        existing,
    )
    if not target:
        return _make_result(
            False,
            error=f"Could not find mission matching '{data.get('target_mission_title') or data.get('target_mission_id')}'.",
        )

    updates = data.get("updates") or {}
    if not updates:
        return _make_result(False, error="No fields to update were specified.")

    # ── Sanitise updates ──
    ALLOWED_FIELDS = {
        "title", "description", "status", "priority", "deadline",
        "scheduled_start", "estimated_minutes", "category", "tags",
        "steps", "meet_url", "notes",
    }
    sanitised = {k: v for k, v in updates.items() if k in ALLOWED_FIELDS}
    if not sanitised:
        return _make_result(False, error="No valid updatable fields found in the request.")

    from infrastructure.tools.mission_tool import MissionTool
    result = MissionTool().update_mission(str(user_id), target["id"], sanitised)
    if not result:
        return _make_result(False, error=f"Failed to update mission '{target['title']}'.")

    content = json.dumps({"action": "update_mission", "mission": result}, ensure_ascii=False)
    return _make_result(
        success=True,
        content=content,
        metadata={"action": "update_mission", "mission_id": target["id"], "updated_fields": list(sanitised.keys())},
    )


# ═══════════════════════════════════════════════════════════════════════════
# Node 3f — delete_mission_node  (Pure DB — no LLM)
# ═══════════════════════════════════════════════════════════════════════════

def delete_mission_node(state: MissionState) -> Dict[str, Any]:
    """Delete a mission. Pure DB — no LLM call needed."""
    user_id = state.get("user_id")
    if not user_id:
        return _make_result(False, error="Cannot delete mission — user not identified.")

    data = state.get("intent_data") or {}
    existing = state.get("existing_missions") or []

    target = _resolve_mission(
        data.get("target_mission_id"),
        data.get("target_mission_title"),
        existing,
    )
    if not target:
        return _make_result(
            False,
            error=f"Could not find mission matching '{data.get('target_mission_title') or data.get('target_mission_id')}'.",
        )

    from infrastructure.tools.mission_tool import MissionTool
    deleted = MissionTool().delete_mission(str(user_id), target["id"])
    if not deleted:
        return _make_result(False, error=f"Failed to delete mission '{target['title']}'.")

    content = json.dumps({"action": "delete_mission", "mission_id": target["id"], "title": target["title"]}, ensure_ascii=False)
    return _make_result(
        success=True,
        content=content,
        metadata={"action": "delete_mission", "mission_id": target["id"]},
    )


# ═══════════════════════════════════════════════════════════════════════════
# Router
# ═══════════════════════════════════════════════════════════════════════════

NODE_LOAD = "load_missions"
NODE_CLASSIFY = "classify"
NODE_CREATE = "create"
NODE_TOGGLE = "toggle_step"
NODE_COMPLETE = "complete_mission"
NODE_QUERY = "query"
NODE_UPDATE = "update_mission"
NODE_DELETE = "delete_mission"


def _route_after_classify(state: MissionState) -> str:
    """Conditional edge: classify → handler node."""
    intent = state.get("intent", "CREATE")
    if intent == "TOGGLE_STEP":
        return NODE_TOGGLE
    if intent == "COMPLETE_MISSION":
        return NODE_COMPLETE
    if intent == "UPDATE":
        return NODE_UPDATE
    if intent == "DELETE":
        return NODE_DELETE
    if intent == "QUERY":
        return NODE_QUERY
    return NODE_CREATE


# ═══════════════════════════════════════════════════════════════════════════
# Build & compile subgraph
# ═══════════════════════════════════════════════════════════════════════════

def build_mission_subgraph(config: Optional["AgentConfig"] = None) -> StateGraph:
    """
    Build (but don't compile) the mission subgraph.

    Returns the StateGraph so the caller can compile it or embed it
    as a subgraph inside the main graph.
    """
    graph = StateGraph(MissionState)

    # ── Nodes ──
    graph.add_node(NODE_LOAD, load_missions_node)
    graph.add_node(NODE_CLASSIFY, lambda s: classify_node(s, config=config))
    graph.add_node(NODE_CREATE, lambda s: create_node(s, config=config))
    graph.add_node(NODE_TOGGLE, toggle_step_node)
    graph.add_node(NODE_COMPLETE, complete_mission_node)
    graph.add_node(NODE_QUERY, lambda s: query_node(s, config=config))
    graph.add_node(NODE_UPDATE, lambda s: update_mission_node(s, config=config))
    graph.add_node(NODE_DELETE, delete_mission_node)

    # ── Edges ──
    graph.add_edge(START, NODE_LOAD)
    graph.add_edge(NODE_LOAD, NODE_CLASSIFY)
    graph.add_conditional_edges(
        NODE_CLASSIFY,
        _route_after_classify,
        {
            NODE_CREATE: NODE_CREATE,
            NODE_TOGGLE: NODE_TOGGLE,
            NODE_COMPLETE: NODE_COMPLETE,
            NODE_QUERY: NODE_QUERY,
            NODE_UPDATE: NODE_UPDATE,
            NODE_DELETE: NODE_DELETE,
        },
    )
    # All handler nodes → END
    graph.add_edge(NODE_CREATE, END)
    graph.add_edge(NODE_TOGGLE, END)
    graph.add_edge(NODE_COMPLETE, END)
    graph.add_edge(NODE_QUERY, END)
    graph.add_edge(NODE_UPDATE, END)
    graph.add_edge(NODE_DELETE, END)

    return graph


# ═══════════════════════════════════════════════════════════════════════════
# Main-graph adapter
# ═══════════════════════════════════════════════════════════════════════════

def create_mission_node(config: Optional["AgentConfig"] = None):
    """
    Factory that returns a node function compatible with the main graph.

    The main graph calls:
        graph.add_node(NODE_MISSION, create_mission_node(config))

    Input:  AgentState  (from the main graph)
    Output: dict        (worker_results, gathered_context, etc.)

    Internally it runs the compiled mission subgraph synchronously.
    """
    from langchain_core.messages import BaseMessage

    subgraph = build_mission_subgraph(config=config).compile()

    def mission_node(state: Dict[str, Any]) -> Dict[str, Any]:
        log_info("=== Mission SubGraph Node ===")

        # ── Adapt main-graph state → MissionState ──
        question = state.get("original_question", "")
        context = state.get("gathered_context", "")
        user_id = state.get("user_id")
        if not user_id:
            meta = state.get("metadata") or {}
            user_id = meta.get("user_id")

        # Build history text
        msgs: list = list(state.get("messages") or [])
        tail = msgs[-8:] if len(msgs) > 8 else msgs
        history_parts: list[str] = []
        for m in tail:
            role = getattr(m, "type", "unknown")
            c = str(getattr(m, "content", "") or "")[:500]
            history_parts.append(f"[{role}] {c}")
        history_text = "\n".join(history_parts)

        if history_text:
            context = f"{history_text}\n\n{context}" if context else history_text

        mission_input: MissionState = {
            "question": question,
            "context": context,
            "history": history_text,
            "user_id": str(user_id) if user_id else None,
        }

        # ── Run the subgraph ──
        final = subgraph.invoke(mission_input)

        # ── Adapt result → main-graph state update ──
        result_data = final.get("result") or {}
        worker_result = WorkerResult(
            worker_type=WorkerType.MISSION,
            success=result_data.get("success", False),
            content=result_data.get("content", ""),
            error=result_data.get("error"),
            metadata=result_data.get("metadata", {}),
        )

        worker_results = list(state.get("worker_results") or [])
        worker_results.append(worker_result)

        gathered = state.get("gathered_context") or ""
        # For query, the gathered_context comes from the node itself;
        # for mutations/creates, we append the content.
        extra_context = result_data.get("gathered_context") or ""
        if not extra_context and worker_result.success and worker_result.content:
            extra_context = worker_result.content
        if extra_context:
            gathered = gathered + f"\n\n=== MISSION ===\n{extra_context}"

        timing = dict(state.get("timing") or {})
        timing["mission_ms"] = worker_result.execution_time_ms

        # Build a human-readable summary for the completed_actions entry
        action = (worker_result.metadata or {}).get("action", "")
        if action == "create" and worker_result.success and worker_result.content:
            import json as _json3
            try:
                missions_created = _json3.loads(worker_result.content)
                titles = [m.get("title", "?") for m in missions_created[:3]]
                action_summary = f"Created: {', '.join(repr(t) for t in titles)}"
            except Exception:
                action_summary = worker_result.content[:120]
        elif worker_result.success and worker_result.content:
            action_summary = worker_result.content[:120].replace("\n", " ")
        elif worker_result.error:
            action_summary = worker_result.error[:120]
        else:
            action_summary = "no output"

        fingerprint = f"mission:{action}:{worker_result.success}"
        completed = list(state.get("completed_actions") or [])
        completed.append({
            "worker": "mission",
            "action": action,
            "success": worker_result.success,
            "fingerprint": fingerprint,
            "summary": action_summary,
        })

        return {
            "worker_results": worker_results,
            "gathered_context": gathered,
            "current_worker": None,
            "timing": timing,
            "completed_actions": completed,
        }

    return mission_node
