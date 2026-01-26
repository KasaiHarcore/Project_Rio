"""LangGraph streaming workflow runner."""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage

from backend.core.settings import AgentConfig
from backend.db.models.run import RunStatus
from backend.services.llm import form
from backend.services.run_service import run_service
from backend.utils.log import log_error
from uuid import UUID

from backend.db.session import get_db_context
from backend.db.repositories.state_checkpoint_repo import StateCheckpointRepository
from backend.db.models.state_checkpoint import StateCheckpoint
from backend.workflows.checkpointing import checkpoint_context, get_latest_checkpoint_info
from backend.workflows.graph_definition import build_config_payload, build_graph, extract_answer


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
	collected_messages: List[BaseMessage] = []
	buffer = ""

	try:
		with checkpoint_context() as checkpointer:
			graph = build_graph(
				tools=tools or [],
				system_prompt=system_prompt,
				checkpointer=checkpointer,
			)
			for chunk, _metadata in graph.stream(
				{"question": question, "history": history or []},
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
		yield {"type": "final", "result": {"answer": answer, "stats": stats}, "run_id": run_id}
	except Exception as e:
		run_service.finish_run(run_id=run_id, status=RunStatus.FAILED, error=str(e))
		log_error(f"LangGraph streaming failed: {e}")
		yield {"type": "error", "error": str(e), "run_id": run_id}
