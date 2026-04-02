"""Arize Phoenix tracing configuration.

LLM calls, tool calls, and LangGraph nodes are **auto-instrumented** by the
`openinference-instrumentation-langchain` package once the OTEL tracer
provider is registered via `phoenix.otel.register()`.

This module provides lightweight helpers to:
- Check whether tracing is active
- Build metadata for ``RunnableConfig`` (so auto-traces carry business context)
- A context manager to scope trace metadata cleanly

Terminal and Database logging already cover operational concerns (errors, progress).
Phoenix is reserved for what only it can show:
  → full LLM call-chain visualisation
  → token-level cost attribution
  → retrieval chunk inspection
  → multi-agent decision replay
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from utils.log import log_debug, log_info, log_warning

# Lock to protect one-time initialisation
_init_lock = threading.Lock()
_initialized = False


# ─── One-time OTEL bootstrap ───────────────────────────────────────────

def _ensure_initialized() -> None:
	"""Register the Phoenix OTEL tracer provider exactly once.

	Called lazily on first ``tracing_enabled()`` check so that imports
	of this module never have side effects.
	"""
	global _initialized
	if _initialized:
		return

	with _init_lock:
		if _initialized:
			return

		if not _is_phoenix_enabled():
			_initialized = True
			return

		try:
			from phoenix.otel import register

			endpoint = os.getenv(
				"PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006"
			)
			project = project_name()

			register(
				project_name=project,
				endpoint=endpoint,
				auto_instrument=True,  # auto-instruments LangChain/LangGraph
			)
			log_info(
				f"Phoenix OTEL tracer registered "
				f"(endpoint={endpoint}, project={project})"
			)
		except Exception as exc:
			log_warning(f"Failed to initialise Phoenix tracing: {exc}")

		_initialized = True


# ─── Environment helpers ───────────────────────────────────────────────

def _is_phoenix_enabled() -> bool:
	"""Raw check without triggering initialisation."""
	raw = os.getenv("PHOENIX_ENABLED", "false")
	return raw.strip().lower() in {"1", "true", "yes"}


def tracing_enabled() -> bool:
	"""Return True when Phoenix tracing is active for this process."""
	_ensure_initialized()
	return _is_phoenix_enabled()


def project_name() -> str:
	"""Return the Phoenix project name from environment."""
	return os.getenv("PHOENIX_PROJECT_NAME") or "ai-agent"


def apply_user_phoenix_settings(
	*,
	tracing_enabled: bool,
	project: Optional[str],
) -> None:
	"""Apply per-user Phoenix settings.

	For self-hosted Phoenix there is no per-user API key; the only
	per-user knobs are the on/off toggle and the project name.
	We set environment variables that ``_ensure_initialized`` reads
	so the next request picks up the change.
	"""
	if tracing_enabled:
		os.environ["PHOENIX_ENABLED"] = "true"
		if project:
			os.environ["PHOENIX_PROJECT_NAME"] = project
		log_debug(f"Phoenix tracing enabled (project={project or 'default'})")
	else:
		os.environ["PHOENIX_ENABLED"] = "false"
		log_debug("Phoenix tracing disabled by user settings")

	# Force re-initialisation on next check so new settings take effect
	global _initialized
	_initialized = False


# ─── Config builder — inject business context into auto-traces ─────────

def build_trace_metadata(
	*,
	run_name: str,
	tags: Optional[List[str]] = None,
	metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
	"""
 	Build fields to merge into a LangChain ``RunnableConfig``.

	Usage:

		cfg = {**checkpoint_config, **build_trace_metadata(...)}
		graph.invoke(state, config=cfg)
	"""
	if not tracing_enabled():
		return {}

	result: Dict[str, Any] = {"run_name": run_name}
	if tags:
		result["tags"] = [t.strip()[:128] for t in tags if t and t.strip()]
	if metadata:
		result["metadata"] = metadata
	return result


@contextmanager
def workflow_trace(
	*,
	name: str,
	tags: Optional[List[str]] = None,
	metadata: Optional[Dict[str, Any]] = None,
) -> Iterator[Optional[Dict[str, Any]]]:
	"""
 	Context manager that yields trace config to merge into `RunnableConfig`.

	Usage:

		with workflow_trace(name="...", tags=[...], metadata={...}) as trace_cfg:
			config_payload.update(trace_cfg or {})
			graph.invoke(state, config=config_payload)
	"""
	yield build_trace_metadata(run_name=name, tags=tags, metadata=metadata)


# ─── Developer hint ────────────────────────────────────────────────────

def log_trace_hint(run_id: str) -> None:
	"""Print where to find traces (terminal only, no cost)."""
	if tracing_enabled():
		endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006")
		log_info(f"Phoenix tracing active (run_id={run_id}, project={project_name()}, ui={endpoint})")
	else:
		log_debug("Phoenix tracing disabled — set PHOENIX_ENABLED=true")
