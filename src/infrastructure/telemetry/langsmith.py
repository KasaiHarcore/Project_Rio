"""LangSmith tracing configuration.

LLM calls, tool calls, and LangGraph nodes are **auto-traced** by LangChain
when LANGSMITH_TRACING=true (or LANGCHAIN_TRACING_V2=true) + an API key is set.

This module provides lightweight helpers to:
- Check whether tracing is active
- Build metadata for ``RunnableConfig`` (so auto-traces carry business context)
- A context manager to scope trace metadata cleanly

Terminal and Database logging already cover operational concerns (errors, progress).
LangSmith is reserved for what only it can show:
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

from utils.log import log_debug, log_info

# Lock to protect os.environ mutations (LangChain auto-tracing reads env vars)
_env_lock = threading.Lock()


# Environment helpers

def tracing_enabled() -> bool:
	"""Return True when LangSmith tracing is active for this process."""
	has_key = bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))
	raw = os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2")
	if raw is None:
		return has_key
	return raw.strip().lower() in {"1", "true", "yes"}


def project_name() -> str:
	"""Return the LangSmith project name from environment."""
	return (
		os.getenv("LANGSMITH_PROJECT")
		or os.getenv("LANGCHAIN_PROJECT")
		or "ai-agent"
	)


def apply_user_langsmith_settings(
	*,
	api_key: Optional[str],
	tracing_enabled: bool,
	project: Optional[str],
) -> None:
	"""Apply per-user LangSmith settings as environment variables.

	LangChain auto-tracing reads from env vars, so we set them here
	before the workflow graph is invoked. Call this at the start of each
	request when user settings are available.
	"""
	with _env_lock:
		if tracing_enabled and api_key:
			os.environ["LANGSMITH_API_KEY"] = api_key
			os.environ["LANGSMITH_TRACING"] = "true"
			if project:
				os.environ["LANGSMITH_PROJECT"] = project
			log_debug(f"LangSmith tracing enabled (project={project or 'default'})")
		elif not tracing_enabled:
			os.environ["LANGSMITH_TRACING"] = "false"
			log_debug("LangSmith tracing disabled by user settings")


# Config builder — inject business context into auto-traces

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


# Developer hint

def log_trace_hint(run_id: str) -> None:
	"""Print where to find traces (terminal only, no cost)."""
	if tracing_enabled():
		log_info(f"LangSmith tracing active (run_id={run_id}, project={project_name()})")
	else:
		log_debug("LangSmith tracing disabled — set LANGSMITH_API_KEY + LANGSMITH_TRACING=true")

