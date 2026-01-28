"""LangGraph streaming workflow runner."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4


from backend.core.settings import AgentConfig
from backend.db.models.run import RunStatus
from backend.services.llm import form
from backend.services.run_service import run_service
from backend.utils.log import log_error
from backend.services.tool_usage_service import clear_tool_logging_context, set_tool_logging_context
from backend.telemetry.langsmith import (
	end_run_error,
	end_run_success,
	log_trace_link_hint,
	traced_span,
	workflow_trace,
)

from backend.workflows.checkpointing import checkpoint_context
from backend.workflows.graph_definition import (
	build_config_payload,
	build_graph,
	build_messages,
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
	current_stage = "init"
	run_service.start_run(
		run_id=run_id,
		thread_id=thread_id,
		mode=config.mode,
		model_name=getattr(form.SELECTED_MODEL, "name", None),
	)
	set_tool_logging_context(thread_id=thread_id, run_id=run_id)
	log_trace_link_hint(run_id)

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
	phase_timings_ms: Dict[str, int] = {}
	root_run = None

	trace_inputs = {
		"question": question,
		"thread_id": thread_id,
		"run_id": run_id,
		"mode": getattr(config, "mode", None),
		"history_items": len(history or []),
	}
	trace_tags = [
		"workflow:langgraph_stream",
		f"mode:{getattr(config, 'mode', 'unknown')}",
		f"model:{getattr(form.SELECTED_MODEL, 'name', 'unknown')}",
	]
	tools_exposed = [getattr(t, "name", "") for t in (tools or []) if getattr(t, "name", "")]

	try:
		with workflow_trace(
			name="agent.stream_workflow",
			run_type="chain",
			inputs=trace_inputs,
			tags=trace_tags,
			metadata={
				"planner_enabled": planner_enabled,
				"reflection_enabled": reflection_enabled,
				"max_retries": max_retries,
				"tools_exposed": tools_exposed,
			},
		) as _root:
			root_run = _root
			with checkpoint_context() as checkpointer:
				for attempt in range(max_retries + 1):
					if planner_enabled:
						current_stage = "planning"
						plan_prompt = build_planning_prompt(
							user_request=question,
							behavior_context=behavior_context,
							mode=config.mode,
						)
						with traced_span(
							name=f"planning.attempt_{attempt+1}",
							run_type="llm",
							inputs={"behavior_context": (behavior_context or "")[:500]},
						) as span:
							plan_text = form.format_markdown_output(_call_llm_text(plan_prompt))
							span.set_outputs({"plan_preview": (plan_text or "")[:1200], "plan_len": len(plan_text or "")})
							phase_timings_ms[f"planning_attempt_{attempt+1}"] = int(span.metadata.get("duration_ms", 0) or 0)
						yield {"type": "planning", "content": plan_text}
						if plan_text:
							system_prompt_with_plan = f"{system_prompt}\n\n{plan_text}"
						else:
							system_prompt_with_plan = system_prompt
					else:
						system_prompt_with_plan = system_prompt

					current_stage = "langgraph.invoke"
					graph = build_graph(
						tools=tools or [],
						system_prompt=system_prompt_with_plan,
						checkpointer=checkpointer,
					)
					initial_messages = build_messages(question=question, history=history or [])
					with traced_span(
						name=f"langgraph.invoke.attempt_{attempt+1}",
						run_type="chain",
						inputs={"history_items": len(history or []), "planning_len": len(plan_text or "")},
					) as span:
						result = graph.invoke(
							{"messages": initial_messages},
							config=config_payload,
						)
						collected_messages = result.get("messages", [])
						answer = extract_answer(collected_messages)
						stats = form.SELECTED_MODEL.get_overall_exec_stats()
						span.set_outputs({"answer_preview": (answer or "")[:1200], "stats": stats})
						phase_timings_ms[f"invoke_attempt_{attempt+1}"] = int(span.metadata.get("duration_ms", 0) or 0)

					if not reflection_enabled:
						break

					current_stage = "reflection"
					tool_context = extract_tool_context(collected_messages)
					refl_prompt = build_reflection_prompt(
						user_request=question,
						plan=plan_text,
						result_context=tool_context,
						answer=answer,
						mode=config.mode,
					)
					with traced_span(
						name=f"reflection.attempt_{attempt+1}",
						run_type="llm",
						inputs={"tool_context_len": len(tool_context or "")},
					) as span:
						reflection_text = form.format_markdown_output(_call_llm_text(refl_prompt))
						reflection_attempts = attempt + 1
						reflection_valid = _is_valid_reflection(reflection_text)
						span.set_outputs({"valid": bool(reflection_valid), "reflection_preview": (reflection_text or "")[:1200]})
						phase_timings_ms[f"reflection_attempt_{attempt+1}"] = int(span.metadata.get("duration_ms", 0) or 0)
					yield {"type": "reflection", "content": reflection_text}
					if reflection_valid:
						break
					reflection_feedback = _extract_feedback(reflection_text)
					behavior_context = reflection_feedback or None

				# After planning/reflection loop, stream the final answer from the graph
				current_stage = "langgraph.stream"
				buffer = ""
				collected_messages = []
				graph = build_graph(
					tools=tools or [],
					system_prompt=system_prompt_with_plan,
					checkpointer=checkpointer,
				)
				with traced_span(
					name="langgraph.stream",
					run_type="chain",
					inputs={"planning_len": len(plan_text or "")},
				) as span:
					for chunk, _metadata in graph.stream(
						{"messages": initial_messages},
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
					span.set_outputs({"answer_len": len(answer or ""), "stats": stats})
					phase_timings_ms["stream"] = int(span.metadata.get("duration_ms", 0) or 0)

		run_service.finish_run(run_id=run_id, status=RunStatus.SUCCEEDED)
		end_run_success(
			run=root_run,
			outputs={"answer_preview": (answer or "")[:2000], "stats": stats},
			metadata={"timings_ms": phase_timings_ms, "reflection_valid": bool(reflection_valid)},
		)
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
		end_run_error(run=root_run, error=e, metadata={"failed_stage": current_stage, "run_id": run_id})
		log_error(f"LangGraph streaming failed: {e}")
		yield {"type": "error", "error": str(e), "run_id": run_id}
	finally:
		clear_tool_logging_context()
