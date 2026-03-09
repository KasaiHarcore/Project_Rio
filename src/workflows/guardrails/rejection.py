"""Hardcoded rejection node for guardrail failures.

Returns a safe, generic rejection message and marks the execution as completed.
"""

from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import AIMessage

from utils.log import log_info
from workflows.state import ExecutionStatus


_INPUT_REJECTION_MESSAGE = (
    "I'm sorry, but I can't process that request. "
    "Please try rephrasing your question about studying or learning, "
    "and I'll be happy to help!"
)

_OUTPUT_REJECTION_MESSAGE = (
    "I apologize, but I'm unable to provide a response to that query at this time. "
    "Please try asking your question in a different way."
)


def guardrail_reject_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Guardrail rejection node.

    Returns a hardcoded rejection message based on which guardrail failed,
    sets ``final_response``, and marks the execution as completed.
    """
    log_info("=== Guardrail Reject Node ===")

    # Determine which guardrail triggered the rejection
    if state.get("guardrail_passed") is False:
        rejection_message = _INPUT_REJECTION_MESSAGE
        source = "input"
    elif state.get("guardrail_output_passed") is False:
        rejection_message = _OUTPUT_REJECTION_MESSAGE
        source = "output"
    else:
        rejection_message = _INPUT_REJECTION_MESSAGE
        source = "unknown"

    log_info(f"[Guardrail] Rejected by {source} guardrail")

    messages = list(state.get("messages") or [])
    messages.append(AIMessage(content=rejection_message))

    return {
        "messages": messages,
        "final_response": rejection_message,
        "status": ExecutionStatus.COMPLETED,
    }
