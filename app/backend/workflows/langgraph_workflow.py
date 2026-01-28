"""LangGraph workflow orchestration for agent execution."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from backend.core.settings import AgentConfig
from backend.db.models.run import RunStatus
from backend.services.llm import form
from backend.services.run_service import run_service
from backend.utils.log import log_error, log_warning, log_info, log_success
from backend.services.tool_usage_service import clear_tool_logging_context, set_tool_logging_context
from backend.telemetry.langsmith import (
	end_run_error,
	end_run_success,
	log_trace_link_hint,
	traced_span,
	workflow_trace,
)
from backend.workflows.checkpointing import (
	checkpoint_context,
	list_checkpoints as _list_checkpoints,
	load_checkpoint as _load_checkpoint,
)
from backend.workflows.graph_definition import (
	build_config_payload,
	build_graph,
	build_messages,
	extract_answer,
	extract_tool_context,
)
from backend.workflows.planning import build_planning_prompt
from backend.workflows.reflection import build_reflection_prompt


def run_workflow(
	*,
	question: str,
	config: AgentConfig,
	history: Optional[List[Dict[str, Any]]] = None,
	thread_id: Optional[str] = None,
	checkpoint_id: Optional[str] = None,
	checkpoint_ns: Optional[str] = None,
	tools: Optional[List[Any]] = None,
	system_prompt: str = "",
) -> Dict[str, Any]:
	"""
	Execute the LangGraph workflow and return the final answer.
	"""
	thread_id = thread_id or str(uuid4())
	
	# Initialize run tracking
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

	# Configuration
	planner_enabled = bool(getattr(config, "enable_planner", True))
	reflection_enabled = bool(getattr(config, "enable_reflection", True))
	max_retries = int(getattr(config, "verify_max_retries", 0) or 0) if reflection_enabled else 0
	
	# State variables
	behavior_context: Optional[str] = None
	plan_text = ""
	reflection_text = ""
	reflection_valid = False
	answer = ""
	stats: Dict[str, Any] = {}
	reflection_feedback = ""
	reflection_attempts = 0
	phase_timings_ms: Dict[str, int] = {}
	tool_names_used: List[str] = []

	trace_inputs = {
		"question": question,
		"thread_id": thread_id,
		"run_id": run_id,
		"mode": getattr(config, "mode", None),
		"history_items": len(history or []),
	}
	tools_exposed = [getattr(t, "name", "") for t in (tools or []) if getattr(t, "name", "")]
	trace_tags = [
		"workflow:langgraph",
		f"mode:{getattr(config, 'mode', 'unknown')}",
		f"model:{getattr(form.SELECTED_MODEL, 'name', 'unknown')}",
	]

	root_run = None
	try:
		with workflow_trace(
			name="agent.run_workflow",
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
			# Execute LangGraph workflow with checkpointing
			with checkpoint_context() as checkpointer:
				for attempt in range(max_retries + 1):
					# Planning phase
					if planner_enabled:
						current_stage = "planning"
						log_info(f"Generating plan for question (attempt {attempt + 1})")
						plan_prompt = build_planning_prompt(
							user_request=question,
							behavior_context=behavior_context,
							mode=config.mode,
						)
						with traced_span(
							name=f"planning.attempt_{attempt+1}",
							run_type="llm",
							inputs={
								"mode": getattr(config, "mode", None),
								"behavior_context": (behavior_context or "")[:500],
							},
						) as span:
							plan_text = form.format_markdown_output(_call_llm_text(plan_prompt))
							span.set_outputs(
								{
									"plan_preview": (plan_text or "")[:1200],
									"plan_len": len(plan_text or ""),
								}
							)
							phase_timings_ms[f"planning_attempt_{attempt+1}"] = int(span.metadata.get("duration_ms", 0) or 0)
						if plan_text:
							system_prompt_with_plan = f"{system_prompt}\n\n{plan_text}"
						else:
							system_prompt_with_plan = system_prompt
					else:
						system_prompt_with_plan = system_prompt

					# Build and execute graph
					current_stage = "build_graph"
					log_info(f"Building LangGraph with {len(tools or [])} tools")
					with traced_span(
						name="langgraph.build_graph",
						run_type="chain",
						inputs={"tools_count": len(tools or [])},
					) as span:
						graph = build_graph(
							tools=tools or [],
							system_prompt=system_prompt_with_plan,
							checkpointer=checkpointer,
						)
						span.set_outputs({"ok": True})

					current_stage = "langgraph.invoke"
					log_info("Invoking LangGraph workflow")
					initial_messages = build_messages(question=question, history=history or [])
					with traced_span(
						name=f"langgraph.invoke.attempt_{attempt+1}",
						run_type="chain",
						inputs={
							"question_preview": (question or "")[:500],
							"history_items": len(history or []),
							"planning_len": len(plan_text or ""),
						},
					) as span:
						result = graph.invoke(
							{"messages": initial_messages},
							config=config_payload,
						)
						messages = result.get("messages", [])
						answer = extract_answer(messages)
						stats = form.SELECTED_MODEL.get_overall_exec_stats()

						# What did agent do? (tool calls)
						tool_names_used = []
						for msg in messages or []:
							calls = getattr(msg, "tool_calls", None) or []
							for call in calls:
								name = (call or {}).get("name") if isinstance(call, dict) else None
								if name:
									tool_names_used.append(str(name))
						span.set_outputs(
							{
								"answer_preview": (answer or "")[:1200],
								"answer_len": len(answer or ""),
								"messages_count": len(messages or []),
								"tools_used": tool_names_used,
								"cost": stats,
							}
						)
						phase_timings_ms[f"invoke_attempt_{attempt+1}"] = int(span.metadata.get("duration_ms", 0) or 0)
					log_success(f"LangGraph execution completed (attempt {attempt + 1})")

					# Reflection phase
					if not reflection_enabled:
						break

					current_stage = "reflection"
					tool_context = extract_tool_context(messages)
					log_info("Running reflection validation")
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
						inputs={
							"plan_len": len(plan_text or ""),
							"answer_len": len(answer or ""),
							"tool_context_len": len(tool_context or ""),
						},
					) as span:
						reflection_text = form.format_markdown_output(_call_llm_text(refl_prompt))
						reflection_attempts = attempt + 1
						reflection_valid = _is_valid_reflection(reflection_text)
						span.set_outputs(
							{
								"reflection_preview": (reflection_text or "")[:1200],
								"reflection_len": len(reflection_text or ""),
								"valid": bool(reflection_valid),
							}
						)
						phase_timings_ms[f"reflection_attempt_{attempt+1}"] = int(span.metadata.get("duration_ms", 0) or 0)
					if reflection_valid:
						log_success("Reflection validation passed")
						break
					log_warning(f"Reflection validation failed (attempt {attempt + 1})")
					reflection_feedback = _extract_feedback(reflection_text)
					behavior_context = reflection_feedback or None

				# Update result with planning/reflection metadata
				result["planning"] = plan_text
				result["reflection"] = reflection_text
				result["reflection_valid"] = reflection_valid
				result["reflection_feedback"] = reflection_feedback
				result["reflection_attempts"] = reflection_attempts

			# Mark run as succeeded
			run_service.finish_run(run_id=run_id, status=RunStatus.SUCCEEDED)
			end_run_success(
				run=root_run,
				outputs={
					"answer_preview": (answer or "")[:2000],
					"stats": stats,
					"tools_used": tool_names_used,
					"reflection_valid": reflection_valid,
					"reflection_attempts": reflection_attempts,
					"reflection_feedback": (reflection_feedback or "")[:2000],
				},
				metadata={
					"timings_ms": phase_timings_ms,
					"why": {
						"planner_enabled": planner_enabled,
						"reflection_enabled": reflection_enabled,
						"replan_feedback": (reflection_feedback or "")[:2000],
					},
				},
			)
			log_success(f"Workflow completed successfully: run_id={run_id}")
			return {
				"answer": answer,
				"stats": stats,
				"run_id": run_id,
				"planning": plan_text,
				"reflection": reflection_text,
				"reflection_valid": reflection_valid,
				"reflection_feedback": reflection_feedback,
				"reflection_attempts": reflection_attempts,
			}
	except Exception as e:
		run_service.finish_run(run_id=run_id, status=RunStatus.FAILED, error=str(e))
		end_run_error(run=root_run, error=e, metadata={"failed_stage": current_stage, "run_id": run_id})
		log_error(f"LangGraph workflow failed: {e}")
		raise
	finally:
		clear_tool_logging_context()


def list_checkpoints(
	*,
	thread_id: str,
	checkpoint_ns: str = "",
	limit: int = 20,
	before_checkpoint_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
	"""List checkpoints for a thread (newest first)."""
	return _list_checkpoints(
		thread_id=thread_id,
		checkpoint_ns=checkpoint_ns,
		limit=limit,
		before_checkpoint_id=before_checkpoint_id,
		config_builder=build_config_payload,
	)


def load_checkpoint(
	*,
	thread_id: str,
	checkpoint_id: str,
	checkpoint_ns: str = "",
) -> Optional[Dict[str, Any]]:
	"""Load a checkpoint tuple for time-travel."""
	return _load_checkpoint(
		thread_id=thread_id,
		checkpoint_id=checkpoint_id,
		checkpoint_ns=checkpoint_ns,
		config_builder=build_config_payload,
	)