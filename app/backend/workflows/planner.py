"""Planning workflow for multi-step actions and tool use."""

from __future__ import annotations

from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage

from backend.services.llm import form
from backend.utils.log import log_debug, log_warning, log_error


def run_planner(*, question: str, mode: str) -> Optional[str]:
	"""Generate a lightweight plan for the next action."""
	if not form.SELECTED_MODEL or not form.SELECTED_MODEL.llm:
		log_warning("Planner skipped: no active LLM model")
		return None

	log_debug(f"Planner started (mode={mode})")

	planner_prompt = (
		"You are a planning assistant. Provide a short plan (max 3 steps) "
		"for answering the user's question. Do not answer the question."
	)
	messages = [
		SystemMessage(content=planner_prompt),
		HumanMessage(content=f"Mode: {mode}\nQuestion: {question}"),
	]
	try:
		response = form.SELECTED_MODEL.llm.invoke(messages)
		plan = (getattr(response, "content", "") or "").strip() or None
		if plan:
			log_debug("Planner produced a plan")
		else:
			log_warning("Planner returned empty plan")
		return plan
	except Exception as e:
		log_error(f"Planner failed: {e}")
		return None