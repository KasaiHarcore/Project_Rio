"""
Checkpoint listing and loading wrappers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from workflows.checkpointer import (
    list_checkpoints as _list_checkpoints,
    load_checkpoint as _load_checkpoint,
)


def list_checkpoints(
    *,
    thread_id: str,
    checkpoint_ns: str = "",
    limit: int = 20,
    before_checkpoint_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List checkpoints for a thread.

    Args:
        thread_id: Thread to list checkpoints for
        checkpoint_ns: Namespace filter
        limit: Maximum results
        before_checkpoint_id: Pagination cursor

    Returns:
        List of checkpoint metadata
    """
    return _list_checkpoints(
        thread_id=thread_id,
        checkpoint_ns=checkpoint_ns,
        limit=limit,
        before_checkpoint_id=before_checkpoint_id,
    )


def load_checkpoint(
    *,
    thread_id: str,
    checkpoint_id: str,
    checkpoint_ns: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Load a specific checkpoint.

    Args:
        thread_id: Thread the checkpoint belongs to
        checkpoint_id: Checkpoint to load
        checkpoint_ns: Namespace

    Returns:
        Checkpoint data or None
    """
    return _load_checkpoint(
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )
