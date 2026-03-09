"""Output guardrail node for the LangGraph workflow.

Runs deterministic checks (PII regex, system prompt leak patterns) and
an LLM-based content safety check on the final response before returning
it to the user.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict

from utils.log import log_debug, log_info, log_warning

from workflows.guardrails.schemas import OutputCheckResult

GUARDRAILS_FAIL_OPEN = os.getenv("GUARDRAILS_FAIL_OPEN", "true").lower() == "true"

# PII patterns
_PII_PATTERNS = [
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "email address"),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "phone number"),
    (r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "SSN"),
    (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b", "credit card number"),
]

# System prompt leak indicators
_SYSTEM_LEAK_PATTERNS = [
    r"(?i)system\s*prompt",
    r"(?i)you\s+are\s+an?\s+AI\s+(?:assistant|agent|model)",
    r"(?i)my\s+(?:instructions|system\s*message)\s+(?:say|are|tell)",
    r"(?i)here\s+(?:is|are)\s+my\s+(?:full\s+)?(?:instructions|prompt|system\s*(?:prompt|message))",
]

OUTPUT_CHECK_PROMPT = """You are a safety classifier reviewing an AI assistant's response before it is sent to the user. Analyze the following output and determine:

1. **is_safe**: Is this response safe and appropriate? (no instructions for harm, no hate speech)
2. **contains_system_leak**: Does this response reveal internal system prompts, instructions, or configuration details that should be kept private?
3. **contains_harmful_content**: Does this response contain harmful, violent, illegal, or inappropriate content?

AI response:
---
{output_text}
---

Respond with your analysis."""


def _check_pii(text: str) -> tuple[bool, str]:
    """Regex-based PII detection.

    Returns (passed, reason). Passes if no PII found.
    """
    for pattern, pii_type in _PII_PATTERNS:
        if re.search(pattern, text):
            return False, f"Output contains potential {pii_type}"
    return True, ""


def _check_system_leak(text: str) -> tuple[bool, str]:
    """Deterministic check for system prompt fragment patterns.

    Returns (passed, reason).
    """
    for pattern in _SYSTEM_LEAK_PATTERNS:
        if re.search(pattern, text):
            return False, "Output may contain system prompt leakage"
    return True, ""


def _check_content_safety(text: str) -> tuple[bool, str]:
    """LLM-based output content safety check.

    Returns (passed, reason). Fail-open on errors.
    """
    try:
        from infrastructure.llm import form

        if not form.SELECTED_MODEL or not form.SELECTED_MODEL.llm:
            if form.SELECTED_MODEL:
                form.SELECTED_MODEL.setup()
            else:
                log_warning("[OutputGuardrail] No LLM available, fail-open")
                return True, ""

        llm = form.SELECTED_MODEL.llm
        structured_llm = llm.with_structured_output(OutputCheckResult)

        prompt = OUTPUT_CHECK_PROMPT.format(output_text=text[:3000])
        result: OutputCheckResult = structured_llm.invoke(prompt)

        if result.contains_system_leak:
            return False, result.rejection_reason or "System prompt leakage detected in output"

        if result.contains_harmful_content:
            return False, result.rejection_reason or "Harmful content detected in output"

        if not result.is_safe:
            return False, result.rejection_reason or "Output flagged as unsafe"

        return True, ""

    except Exception as e:
        log_warning(f"[OutputGuardrail] LLM check failed: {e}")
        if GUARDRAILS_FAIL_OPEN:
            return True, ""
        return False, f"Output guardrail check unavailable: {e}"


def output_guardrail_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Output guardrail LangGraph node.

    Runs all checks on ``final_response``. Sets ``guardrail_output_passed``
    and ``guardrail_output_rejection`` in state.
    """
    log_info("=== Output Guardrail Node ===")

    text = state.get("final_response") or ""

    if not text:
        log_debug("[OutputGuardrail] No final_response to check, passing through")
        return {
            "guardrail_output_passed": True,
            "guardrail_output_rejection": None,
        }

    # 1. Deterministic PII check
    passed, reason = _check_pii(text)
    if not passed:
        log_warning(f"[OutputGuardrail] Rejected (PII): {reason}")
        return {
            "guardrail_output_passed": False,
            "guardrail_output_rejection": reason,
        }

    # 2. Deterministic system leak check
    passed, reason = _check_system_leak(text)
    if not passed:
        log_warning(f"[OutputGuardrail] Rejected (system leak): {reason}")
        return {
            "guardrail_output_passed": False,
            "guardrail_output_rejection": reason,
        }

    # 3. LLM-based content safety check
    passed, reason = _check_content_safety(text)
    if not passed:
        log_warning(f"[OutputGuardrail] Rejected (LLM): {reason}")
        return {
            "guardrail_output_passed": False,
            "guardrail_output_rejection": reason,
        }

    log_debug("[OutputGuardrail] Output passed all checks")
    return {
        "guardrail_output_passed": True,
        "guardrail_output_rejection": None,
    }


def route_after_output_guardrail(state: Dict[str, Any]) -> str:
    """Route after output guardrail: to END if passed, reject if failed."""
    if state.get("guardrail_output_passed", True):
        return "__end__"
    return "guardrail_reject"
