"""Reflection/self-ask logic to improve answer quality."""

from __future__ import annotations

from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage

from backend.services.llm import form
from backend.utils.log import log_debug, log_warning, log_error


def run_reflection(*, question: str, answer: str) -> Optional[str]:
	"""Return brief reflection notes to improve answer quality."""
	if not form.SELECTED_MODEL or not form.SELECTED_MODEL.llm:
		log_warning("Reflection skipped: no active LLM model")
		return None

	log_debug("Reflection started")

	reflection_prompt = (
		"You are a reviewer. Provide concise feedback on the answer quality. "
		"Return a short note (max 2 sentences). Do not rewrite the answer."
	)
	messages = [
		SystemMessage(content=reflection_prompt),
		HumanMessage(content=f"Question: {question}\nAnswer: {answer}"),
	]
	try:
		response = form.SELECTED_MODEL.llm.invoke(messages)
		notes = (getattr(response, "content", "") or "").strip() or None
		if notes:
			log_debug("Reflection produced notes")
		else:
			log_warning("Reflection returned empty notes")
		return notes
	except Exception as e:
		log_error(f"Reflection failed: {e}")
		return None
