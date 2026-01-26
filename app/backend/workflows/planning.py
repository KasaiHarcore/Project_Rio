"""Planning prompt templates for the RAG workflow."""

from __future__ import annotations

from typing import Optional


PLANNING_SYSTEM_PROMPT = """You are a planning assistant. Your job is to produce a concise, step-by-step plan to satisfy the user's request.

Rules:
- Do NOT answer the user.
- Do NOT call or mention any tools.
- Do NOT reference execution details.
- Keep steps concrete and ordered.
- Keep the plan short and focused on essential actions.

Output format (must match exactly):
Planning:
1. <step 1>: What to do
2. <step 2>: What next after step 1
n. <step n>: ...
"""


MODE_GUIDANCE: dict[str, str] = {
    "rag": (
        "Focus on gathering relevant internal policy context and aligning steps with official policy language. "
        "Avoid unnecessary external information."
    ),
    "web": (
        "Focus on identifying trustworthy public sources and verifying time-sensitive facts. "
        "Prefer authoritative sources and keep the plan minimal."
    ),
    "chat": (
        "Decide whether the request needs internal policy context, public information, or both. "
        "Plan only the essential actions to retrieve and synthesize the needed information."
    ),
    "sql": (
        "Focus on identifying required structured records, constraints, and summary goals. "
        "Plan to retrieve only what is necessary and avoid sensitive data."
    ),
}


def build_planning_prompt(
    *,
    user_request: str,
    behavior_context: Optional[str] = None,
    mode: Optional[str] = None,
) -> str:
    """Build the planning prompt.

    Notes:
    - `behavior_context` should describe high-level behavioral constraints or style.
    - It MUST NOT include tool names, execution modes, permissions, or routing logic.
    """
    parts = [PLANNING_SYSTEM_PROMPT]
    if mode:
        guidance = MODE_GUIDANCE.get(mode)
        if guidance:
            parts.append("Mode Guidance:\n" + guidance)
    if behavior_context:
        parts.append("Behavior Context:\n" + behavior_context.strip())
    parts.append("User Request:\n" + (user_request or "").strip())
    return "\n\n".join(parts).strip() + "\n"
