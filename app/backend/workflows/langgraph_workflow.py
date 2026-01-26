"""LangGraph workflow orchestration for agent execution."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from backend.core.settings import AgentConfig
from backend.db.models.run import RunStatus
from backend.services.llm import form
from backend.services.run_service import run_service
from backend.utils.log import log_error, log_warning, log_info, log_success
from backend.workflows.checkpointing import (
	checkpoint_context,
	list_checkpoints as _list_checkpoints,
	load_checkpoint as _load_checkpoint,
)
from backend.workflows.graph_definition import (
	build_config_payload,
	build_graph,
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

	try:
		# Execute LangGraph workflow with checkpointing
		with checkpoint_context() as checkpointer:
			for attempt in range(max_retries + 1):
				# Planning phase
				if planner_enabled:
					log_info(f"Generating plan for question (attempt {attempt + 1})")
					plan_prompt = build_planning_prompt(
						user_request=question,
						behavior_context=behavior_context,
						mode=config.mode,
					)
					plan_text = form.format_markdown_output(_call_llm_text(plan_prompt))
					if plan_text:
						system_prompt_with_plan = f"{system_prompt}\n\n{plan_text}"
					else:
						system_prompt_with_plan = system_prompt
				else:
					system_prompt_with_plan = system_prompt

				# Build and execute graph
				log_info(f"Building LangGraph with {len(tools or [])} tools")
				graph = build_graph(
					tools=tools or [],
					system_prompt=system_prompt_with_plan,
					checkpointer=checkpointer,
				)
				
				log_info("Invoking LangGraph workflow")
				result = graph.invoke(
					{
						"question": question,
						"history": history or [],
						"planning": plan_text,
					},
					config=config_payload,
				)
				
				messages = result.get("messages", [])
				answer = extract_answer(messages)
				stats = form.SELECTED_MODEL.get_overall_exec_stats()
				
				log_success(f"LangGraph execution completed (attempt {attempt + 1})")

				# Reflection phase
				if not reflection_enabled:
					break

				tool_context = extract_tool_context(messages)
				log_info("Running reflection validation")
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
		log_error(f"LangGraph workflow failed: {e}")
		raise


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