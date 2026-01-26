"""LangGraph streaming workflow runner."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4


from backend.core.settings import AgentConfig
from backend.db.models.run import RunStatus
from backend.services.llm import form
from backend.services.run_service import run_service
from backend.utils.log import log_error

from backend.workflows.checkpointing import checkpoint_context
from backend.workflows.graph_definition import (
	build_config_payload,
	build_graph,
	extract_answer,
	extract_tool_context,
)
from langchain_core.messages import AIMessageChunk, BaseMessage
from backend.workflows.planning import build_planning_prompt
from backend.workflows.reflection import build_reflection_prompt


def stream_workflow(
	*,
	question: str,
	config: AgentConfig,
	history: Optional[List[Dict[str, Any]]] = None,
	thread_id: Optional[str] = None,
	checkpoint_id: Optional[str] = None,
	checkpoint_ns: Optional[str] = None,
	tools: Optional[List[Any]] = None,
	system_prompt: str = "",
) -> Iterator[Dict[str, Any]]:
	"""Stream LangGraph output as token and final events."""
	if not thread_id:
		raise ValueError("thread_id is required to map checkpoints to SQL threads")
	run_id = uuid4().hex
	run_service.start_run(
		run_id=run_id,
		thread_id=thread_id,
		mode=config.mode,
		model_name=getattr(form.SELECTED_MODEL, "name", None),
	)

	checkpoint_ns = checkpoint_ns or config.state_scope
	config_payload = build_config_payload(
		thread_id=thread_id,
		checkpoint_id=checkpoint_id,
		checkpoint_ns=checkpoint_ns,
	)

	def _call_llm_text(prompt: str) -> str:
		return form.SELECTED_MODEL.call(user_prompt=prompt, return_text=True)

	def _is_valid_reflection(text: str) -> bool:
		for line in (text or "").splitlines():
			value = line.strip()
			if value:
				return value.upper().startswith("VALID")
		return False

	def _extract_feedback(text: str) -> str:
		lines = [line.strip() for line in (text or "").splitlines()]
		marker = "Feedback for Replanning:"
		if marker in lines:
			idx = lines.index(marker)
			feedback = "\n".join([ln for ln in lines[idx + 1 :] if ln]).strip()
			return feedback
		return text.strip()

	planner_enabled = bool(getattr(config, "enable_planner", True))
	reflection_enabled = bool(getattr(config, "enable_reflection", True))
	max_retries = int(getattr(config, "verify_max_retries", 0) or 0) if reflection_enabled else 0
	behavior_context: Optional[str] = None
	plan_text = ""
	reflection_text = ""
	reflection_valid = False
	answer = ""
	stats: Dict[str, Any] = {}
	reflection_feedback = ""
	reflection_attempts = 0
	collected_messages: List[BaseMessage] = []

	try:
		with checkpoint_context() as checkpointer:
			for attempt in range(max_retries + 1):
				if planner_enabled:
					plan_prompt = build_planning_prompt(
						user_request=question,
						behavior_context=behavior_context,
						mode=config.mode,
					)
					plan_text = form.format_markdown_output(_call_llm_text(plan_prompt))
					yield {"type": "planning", "content": plan_text}
					if plan_text:
						system_prompt_with_plan = f"{system_prompt}\n\n{plan_text}"
					else:
						system_prompt_with_plan = system_prompt
				else:
					system_prompt_with_plan = system_prompt

				graph = build_graph(
					tools=tools or [],
					system_prompt=system_prompt_with_plan,
					checkpointer=checkpointer,
				)
				result = graph.invoke(
					{
						"question": question,
						"history": history or [],
						"planning": plan_text,
					},
					config=config_payload,
				)
				collected_messages = result.get("messages", [])
				answer = extract_answer(collected_messages)
				stats = form.SELECTED_MODEL.get_overall_exec_stats()

				if not reflection_enabled:
					break

				tool_context = extract_tool_context(collected_messages)
				refl_prompt = build_reflection_prompt(
					user_request=question,
					plan=plan_text,
					result_context=tool_context,
					answer=answer,
					mode=config.mode,
				)
				reflection_text = form.format_markdown_output(_call_llm_text(refl_prompt))
				reflection_attempts = attempt + 1
				reflection_valid = _is_valid_reflection(reflection_text)
				yield {"type": "reflection", "content": reflection_text}
				if reflection_valid:
					break
				reflection_feedback = _extract_feedback(reflection_text)
				behavior_context = reflection_feedback or None

			# After planning/reflection loop, stream the final answer from the graph
			buffer = ""
			collected_messages = []
			graph = build_graph(
				tools=tools or [],
				system_prompt=system_prompt_with_plan,
				checkpointer=checkpointer,
			)
			for chunk, _metadata in graph.stream(
				{
					"question": question,
					"history": history or [],
					"planning": plan_text,
				},
				stream_mode="messages",
				config=config_payload,
			):
				if isinstance(chunk, AIMessageChunk):
					text = chunk.content or ""
					if text:
						buffer += text
						yield {"type": "token", "content": text}
					continue
				if isinstance(chunk, BaseMessage):
					collected_messages.append(chunk)

			answer = buffer or extract_answer(collected_messages)
			stats = form.SELECTED_MODEL.get_overall_exec_stats()

		run_service.finish_run(run_id=run_id, status=RunStatus.SUCCEEDED)
		yield {
			"type": "final",
			"result": {
				"answer": answer,
				"stats": stats,
				"planning": plan_text,
				"reflection": reflection_text,
				"reflection_valid": reflection_valid,
				"reflection_feedback": reflection_feedback,
				"reflection_attempts": reflection_attempts,
			},
			"run_id": run_id,
		}
	except Exception as e:
		run_service.finish_run(run_id=run_id, status=RunStatus.FAILED, error=str(e))
		log_error(f"LangGraph streaming failed: {e}")
		yield {"type": "error", "error": str(e), "run_id": run_id}
