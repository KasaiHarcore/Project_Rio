"""Deprecated workflow state persistence.

State snapshots are now handled by LangGraph checkpointers (Postgres), keyed by
thread ID. Use `resolve_checkpoint_thread_id` to map your SQL thread/run IDs to
the checkpointer thread identifier.
"""

from typing import Optional


def resolve_checkpoint_thread_id(
    thread_id: Optional[str],
    run_id: str,
    state_scope: Optional[str] = None,
) -> str:
    """Return the identifier used by LangGraph checkpointer.

    - thread: prefer SQL `thread_id` for stable checkpoint mapping.
    - session/run: use `run_id` for isolated checkpoints.
    - default: fall back to thread_id or run_id.
    """
    scope = (state_scope or "thread").lower()
    if scope in {"session", "run"}:
        return run_id
    if scope == "thread":
        return thread_id or run_id
    return thread_id or run_id
