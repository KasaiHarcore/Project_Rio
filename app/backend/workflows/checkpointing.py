"""LangGraph Postgres checkpoint helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from backend.core.settings import get_app_config


def _normalize_conn_string(conn_string: str) -> str:
	"""Normalize SQLAlchemy DSNs to psycopg-compatible URIs."""
	if conn_string.startswith("postgresql+psycopg2://"):
		return conn_string.replace("postgresql+psycopg2://", "postgresql://", 1)
	if conn_string.startswith("postgresql+psycopg://"):
		return conn_string.replace("postgresql+psycopg://", "postgresql://", 1)
	return conn_string


@contextmanager
def checkpoint_context() -> Iterator[Any]:
	"""Yield a Postgres checkpointer (no fallback)."""
	try:
		from langgraph.checkpoint.postgres import PostgresSaver
		config = get_app_config()
		conn_string = _normalize_conn_string(config.database_url)
		with PostgresSaver.from_conn_string(conn_string) as saver:
			saver.setup()
			yield saver
	except Exception as e:
		raise RuntimeError(f"Failed to initialize LangGraph Postgres checkpointer: {e}") from e


def list_checkpoints(
	*,
	thread_id: str,
	checkpoint_ns: str = "",
	limit: int = 20,
	before_checkpoint_id: Optional[str] = None,
	config_builder,
    ) -> List[Dict[str, Any]]:
	"""List checkpoints for a thread (newest first)."""
	config = config_builder(thread_id=thread_id, checkpoint_ns=checkpoint_ns)
	before = (
		config_builder(
			thread_id=thread_id,
			checkpoint_id=before_checkpoint_id,
			checkpoint_ns=checkpoint_ns,
		)
		if before_checkpoint_id
		else None
	)

	with checkpoint_context() as checkpointer:
		items = []
		for tup in checkpointer.list(config, before=before, limit=limit):
			items.append(
				{
					"checkpoint_id": tup.config["configurable"]["checkpoint_id"],
					"checkpoint_ns": tup.config["configurable"].get("checkpoint_ns", ""),
					"thread_id": tup.config["configurable"]["thread_id"],
					"ts": tup.checkpoint.get("ts"),
					"metadata": tup.metadata,
					"parent_checkpoint_id": (
						tup.parent_config["configurable"]["checkpoint_id"]
						if tup.parent_config
						else None
					),
				}
			)
		return items


def load_checkpoint(
	*,
	thread_id: str,
	checkpoint_id: str,
	checkpoint_ns: str = "",
	config_builder,
) -> Optional[Dict[str, Any]]:
	"""Load a checkpoint tuple for time-travel."""
	config = config_builder(
		thread_id=thread_id,
		checkpoint_id=checkpoint_id,
		checkpoint_ns=checkpoint_ns,
	)
	with checkpoint_context() as checkpointer:
		tup = checkpointer.get_tuple(config)
		if not tup:
			return None
		return {
			"config": tup.config,
			"checkpoint": tup.checkpoint,
			"metadata": tup.metadata,
			"parent_config": tup.parent_config,
			"pending_writes": tup.pending_writes,
		}
