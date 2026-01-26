"""LangGraph workflow orchestration for agent execution."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID
from uuid import uuid4

from backend.core.settings import AgentConfig
from backend.db.models.run import RunStatus
from backend.services.llm import form
from backend.services.run_service import run_service
from backend.utils.log import log_error
from backend.db.session import get_db_context
from backend.db.repositories.state_checkpoint_repo import StateCheckpointRepository
from backend.db.models.state_checkpoint import StateCheckpoint
from backend.workflows.checkpointing import (
	checkpoint_context,
	get_latest_checkpoint_info,
	list_checkpoints as _list_checkpoints,
	load_checkpoint as _load_checkpoint,
)
from backend.workflows.graph_definition import build_config_payload, build_graph, extract_answer


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
	"""Execute the LangGraph workflow and return the final answer."""
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

	try:
		with checkpoint_context() as checkpointer:
			graph = build_graph(
				tools=tools or [],
				system_prompt=system_prompt,
				checkpointer=checkpointer,
			)
			result = graph.invoke(
				{"question": question, "history": history or []},
				config=config_payload,
			)
		messages = result.get("messages", [])
		answer = extract_answer(messages)
		stats = form.SELECTED_MODEL.get_overall_exec_stats()

		try:
			checkpoint_info = get_latest_checkpoint_info(
				thread_id=thread_id,
				checkpoint_ns=checkpoint_ns,
				config_builder=build_config_payload,
			)
			if checkpoint_info:
				thread_uuid = UUID(thread_id)
				with get_db_context() as session:
					repo = StateCheckpointRepository(session)
					round_index = repo.get_next_round_index(thread_uuid)
					checkpoint_row = StateCheckpoint(
						thread_id=thread_uuid,
						run_id=run_id,
						checkpoint_id=checkpoint_info["checkpoint_id"],
						checkpoint_ns=checkpoint_info["checkpoint_ns"],
						parent_checkpoint_id=checkpoint_info.get("parent_checkpoint_id"),
						round_index=round_index,
						checkpoint_metadata=checkpoint_info.get("metadata"),
					)
					repo.create(checkpoint_row)
		except Exception as e:
			log_error(f"Failed to persist checkpoint mapping: {e}")

		run_service.finish_run(run_id=run_id, status=RunStatus.SUCCEEDED)
		return {"answer": answer, "stats": stats, "run_id": run_id}
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
