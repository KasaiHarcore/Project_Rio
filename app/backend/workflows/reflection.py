"""Reflection prompt templates for the RAG workflow."""

from __future__ import annotations

from typing import Optional


REFLECTION_SYSTEM_PROMPT = """You are a reflection assistant. Judge whether the provided result sufficiently answers the user's request.

Rules:
- Do NOT call or mention any tools.
- Do NOT rewrite or improve the answer.
- Do NOT introduce new information.
- Do NOT modify the plan.
- Focus only on sufficiency, alignment, and relevance of the provided information.

Output format (must match exactly):
VALID or INVALID

Evaluation:
<Explanation of why the result is sufficient or insufficient>

Feedback for Replanning:
- <What action was missing, redundant, or insufficient>
- <What should be removed or adjusted in the next plan>
"""


MODE_GUIDANCE: dict[str, str] = {
    "rag": (
        "Judge whether the answer is grounded in internal policy context and omits unsupported claims."
    ),
    "web": (
        "Judge whether the answer is supported by credible public information and is time-appropriate."
    ),
    "chat": (
        "Judge whether the answer uses the right balance of internal context and public information when needed."
    ),
    "sql": (
        "Judge whether the result reflects the correct structured records and satisfies the request without overexposure."
    ),
}


def build_reflection_prompt(
    *,
    user_request: str,
    plan: str,
    result_context: str,
    answer: Optional[str] = None,
    mode: Optional[str] = None,
) -> str:
    """Build the reflection prompt.

    Notes:
    - `result_context` should contain only the retrieved information and observations.
    - It MUST NOT include tool names, execution modes, permissions, or routing logic.
    """
    parts = [REFLECTION_SYSTEM_PROMPT]
    if mode:
        guidance = MODE_GUIDANCE.get(mode)
        if guidance:
            parts.append("Mode Guidance:\n" + guidance)
    parts.append("User Request:\n" + (user_request or "").strip())
    parts.append("Plan:\n" + (plan or "").strip())
    parts.append("Result Context:\n" + (result_context or "").strip())
    if answer is not None:
        parts.append("Answer:\n" + (answer or "").strip())
    return "\n\n".join(parts).strip() + "\n"
