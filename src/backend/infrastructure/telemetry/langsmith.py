"""LangSmith tracing integration and configuration.

This module provides *manual* LangSmith tracing via `langsmith.run_trees.RunTree`.

Why manual tracing (instead of relying only on LANGCHAIN_TRACING_V2)?
- We want deterministic, high-signal spans aligned to this app's workflow phases:
  planning -> langgraph invoke/stream -> reflection -> tool calls.
- We want consistent metadata answering operational questions:
  what the agent did, why, where time/cost went, where it failed, and whether
  it will do better next time.

All helpers are safe no-ops when LangSmith is not configured.
"""

from __future__ import annotations

import os
import time
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional

from backend.utils.log import log_debug, log_error, log_info

try:
	from langsmith.run_trees import RunTree

	_LANGSMITH_AVAILABLE = True
except Exception:  # pragma: no cover
	RunTree = None  # type: ignore[assignment]
	_LANGSMITH_AVAILABLE = False


_CURRENT_RUN_TREE: ContextVar[Optional["RunTree"]] = ContextVar("langsmith_current_run_tree", default=None)


def _utc_now() -> datetime:
	return datetime.now(timezone.utc)


def _truncate(value: Any, limit: int = 2000) -> Any:
	if value is None:
		return None
	if isinstance(value, (int, float, bool)):
		return value
	if isinstance(value, str):
		text = value.strip()
		return text if len(text) <= limit else (text[:limit] + "…")
	# Avoid huge payloads by default
	try:
		text = str(value)
	except Exception:
		return "<unserializable>"
	return text if len(text) <= limit else (text[:limit] + "…")


def _bool_env(name: str, default: bool = False) -> bool:
	raw = os.getenv(name)
	if raw is None:
		return default
	return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def tracing_enabled() -> bool:
	"""Return True if LangSmith tracing should be active for this process."""
	if not _LANGSMITH_AVAILABLE:
		return False

	# LangSmith will use env vars for auth.
	has_key = bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))
	# Default to enabled when an API key is present.
	return _bool_env("LANGSMITH_TRACING", default=has_key)


def project_name() -> str:
	return (
		os.getenv("LANGSMITH_PROJECT")
		or os.getenv("LANGCHAIN_PROJECT")
		or os.getenv("LANGSMITH_SESSION")
		or "ai-agent"
	)


def get_current_run_tree() -> Optional["RunTree"]:
	return _CURRENT_RUN_TREE.get()


def _set_current_run_tree(run_tree: Optional["RunTree"]) -> Any:
	return _CURRENT_RUN_TREE.set(run_tree)


def _safe_tags(tags: Optional[list[str]]) -> list[str]:
	result: list[str] = []
	for t in tags or []:
		t2 = (t or "").strip()
		if t2:
			result.append(t2[:128])
	return result


@dataclass
class TraceSpan:
	"""A small handle for adding outputs/metadata to a span."""

	run_tree: Optional["RunTree"]
	outputs: Optional[Dict[str, Any]] = None
	metadata: Dict[str, Any] = field(default_factory=dict)

	def set_outputs(self, outputs: Dict[str, Any]) -> None:
		self.outputs = outputs

	def add_metadata(self, **kwargs: Any) -> None:
		self.metadata.update(kwargs)


@contextmanager
def workflow_trace(
	*,
	name: str,
	run_type: str = "chain",
	inputs: Optional[Dict[str, Any]] = None,
	tags: Optional[list[str]] = None,
	metadata: Optional[Dict[str, Any]] = None,
	extra: Optional[Dict[str, Any]] = None,
) -> Iterator[Optional["RunTree"]]:
	"""Create a root LangSmith run and set it as current for nested spans/tools."""

	if not tracing_enabled():
		token = _set_current_run_tree(None)
		try:
			yield None
		finally:
			_CURRENT_RUN_TREE.reset(token)
		return

	run = RunTree(
		name=name,
		run_type=run_type,
		inputs=inputs or {},
		tags=_safe_tags(tags),
		extra={
			"metadata": metadata or {},
			**(extra or {}),
		},
		session_name=project_name(),
		start_time=_utc_now(),
	)

	try:
		run.post()
	except Exception as e:  # Never break app execution because of tracing.
		log_debug(f"LangSmith trace start skipped: {e}")
		token = _set_current_run_tree(None)
		try:
			yield None
		finally:
			_CURRENT_RUN_TREE.reset(token)
		return

	token = _set_current_run_tree(run)
	try:
		yield run
	finally:
		_CURRENT_RUN_TREE.reset(token)


@contextmanager
def traced_span(
	*,
	name: str,
	run_type: str = "chain",
	inputs: Optional[Dict[str, Any]] = None,
	tags: Optional[list[str]] = None,
	extra: Optional[Dict[str, Any]] = None,
) -> Iterator[TraceSpan]:
	"""Create a child span under the current run.

	This is safe when tracing isn't configured.
	"""

	parent = get_current_run_tree()
	if not tracing_enabled() or parent is None:
		yield TraceSpan(run_tree=None)
		return

	child = parent.create_child(
		name=name,
		run_type=run_type,
		inputs=inputs or {},
		tags=_safe_tags(tags),
		extra=extra or {},
		start_time=_utc_now(),
	)

	try:
		child.post()
	except Exception as e:
		log_debug(f"LangSmith span start skipped: {e}")
		yield TraceSpan(run_tree=None)
		return

	span = TraceSpan(run_tree=child)
	start = time.perf_counter()
	token = _set_current_run_tree(child)
	try:
		yield span
		duration_ms = int((time.perf_counter() - start) * 1000)
		md = {**span.metadata, "duration_ms": duration_ms}
		child.end(outputs=span.outputs, metadata=md)
		child.patch()
	except Exception as e:
		duration_ms = int((time.perf_counter() - start) * 1000)
		md = {**span.metadata, "duration_ms": duration_ms}
		child.end(error=_truncate(str(e), 2000), metadata=md)
		child.patch()
		raise
	finally:
		_CURRENT_RUN_TREE.reset(token)


def end_run_success(
	*,
	run: Optional["RunTree"],
	outputs: Optional[Dict[str, Any]] = None,
	metadata: Optional[Dict[str, Any]] = None,
) -> None:
	if not tracing_enabled() or run is None:
		return
	try:
		run.end(outputs=outputs, metadata=metadata, end_time=_utc_now())
		run.patch()
	except Exception as e:
		log_debug(f"LangSmith trace end skipped: {e}")


def end_run_error(
	*,
	run: Optional["RunTree"],
	error: Exception,
	metadata: Optional[Dict[str, Any]] = None,
) -> None:
	if not tracing_enabled() or run is None:
		return

	err_text = _truncate(str(error), 2000)
	tb = _truncate("".join(traceback.format_exception(type(error), error, error.__traceback__)), 6000)

	md = {**(metadata or {}), "traceback": tb}
	try:
		run.end(error=err_text, metadata=md, end_time=_utc_now())
		run.patch()
	except Exception as e:
		log_debug(f"LangSmith trace error end skipped: {e}")


def log_trace_link_hint(run_id: str) -> None:
	"""Terminal hint: where to find traces. (We can't construct a stable URL without host details.)"""
	if tracing_enabled():
		log_info(f"LangSmith tracing enabled (run_id={run_id}, project={project_name()})")
	else:
		log_debug("LangSmith tracing disabled (set LANGSMITH_API_KEY + LANGSMITH_TRACING=true)")

