"""
PostgreSQL Checkpointing for Durable Execution.

This module provides checkpoint management for LangGraph workflows,
enabling:
- Durable execution that survives crashes
- Time-travel debugging
- Human-in-the-loop state persistence
- State recovery and replay

The checkpointer uses PostgreSQL as the backing store via the
langgraph-checkpoint-postgres package.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from core.settings import get_app_config
from utils.log import log_debug, log_error, log_info, log_warning


def _normalize_conn_string(conn_string: str) -> str:
    """
    Normalize SQLAlchemy DSNs to psycopg-compatible URIs.
    
    LangGraph's PostgresSaver requires standard postgresql:// URIs,
    but SQLAlchemy may use postgresql+psycopg2:// or postgresql+psycopg://.
    """
    if conn_string.startswith("postgresql+psycopg2://"):
        return conn_string.replace("postgresql+psycopg2://", "postgresql://", 1)
    if conn_string.startswith("postgresql+psycopg://"):
        return conn_string.replace("postgresql+psycopg://", "postgresql://", 1)
    return conn_string


def get_connection_string() -> str:
    """Get the normalized PostgreSQL connection string."""
    config = get_app_config()
    return _normalize_conn_string(config.database_url)


@contextmanager
def checkpoint_context() -> Iterator[Any]:
    """
    Context manager that yields a PostgreSQL checkpointer.
    
    Usage:
        with checkpoint_context() as checkpointer:
            graph = build_graph(checkpointer=checkpointer)
            result = graph.invoke(state, config=config_payload, durability="sync")
    
    The checkpointer is automatically set up and torn down.
    
    Raises:
        RuntimeError: If checkpoint initialization fails
    """
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        
        conn_string = get_connection_string()
        log_debug(f"Initializing PostgreSQL checkpointer")
        
        with PostgresSaver.from_conn_string(conn_string) as saver:
            saver.setup()
            log_debug("PostgreSQL checkpointer ready")
            yield saver
            
    except ImportError as e:
        log_error(f"langgraph-checkpoint-postgres not installed: {e}")
        raise RuntimeError(
            "PostgreSQL checkpointing requires langgraph-checkpoint-postgres. "
            "Install with: pip install langgraph-checkpoint-postgres"
        ) from e
    except Exception as e:
        log_error(f"Failed to initialize PostgreSQL checkpointer: {e}")
        raise RuntimeError(f"Checkpoint initialization failed: {e}") from e


def get_checkpointer() -> Any:
    """
    Get a PostgreSQL checkpointer instance.
    
    Note: Caller is responsible for cleanup. Prefer checkpoint_context()
    for automatic resource management.
    
    Returns:
        PostgresSaver instance
    """
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        
        conn_string = get_connection_string()
        saver = PostgresSaver.from_conn_string(conn_string)
        saver.setup()
        return saver
        
    except Exception as e:
        log_error(f"Failed to create checkpointer: {e}")
        raise


def build_config_payload(
    *,
    thread_id: str,
    checkpoint_id: Optional[str] = None,
    checkpoint_ns: str = "",
) -> Dict[str, Any]:
    """
    Build a RunnableConfig payload for LangGraph checkpointing.
    
    Args:
        thread_id: Unique identifier for the conversation thread
        checkpoint_id: Specific checkpoint to resume from (time-travel)
        checkpoint_ns: Namespace for checkpoint isolation
    
    Returns:
        Configuration dictionary for graph.invoke() or graph.stream()
    
    Raises:
        ValueError: If thread_id is not provided
    """
    if not thread_id:
        raise ValueError("thread_id is required for LangGraph checkpointing")
    
    configurable: Dict[str, Any] = {
        "thread_id": str(thread_id),
        "checkpoint_ns": checkpoint_ns or "",
    }
    
    if checkpoint_id:
        configurable["checkpoint_id"] = checkpoint_id
    
    return {"configurable": configurable}


def list_checkpoints(
    *,
    thread_id: str,
    checkpoint_ns: str = "",
    limit: int = 20,
    before_checkpoint_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List checkpoints for a thread (newest first).
    
    This is useful for:
    - Displaying checkpoint history to users
    - Time-travel debugging
    - Implementing undo/redo functionality
    
    Args:
        thread_id: The thread to list checkpoints for
        checkpoint_ns: Namespace filter
        limit: Maximum number of checkpoints to return
        before_checkpoint_id: Return checkpoints before this one (pagination)
    
    Returns:
        List of checkpoint metadata dictionaries
    """
    config = build_config_payload(
        thread_id=thread_id,
        checkpoint_ns=checkpoint_ns,
    )
    
    before = None
    if before_checkpoint_id:
        before = build_config_payload(
            thread_id=thread_id,
            checkpoint_id=before_checkpoint_id,
            checkpoint_ns=checkpoint_ns,
        )
    
    try:
        with checkpoint_context() as checkpointer:
            items = []
            for tup in checkpointer.list(config, before=before, limit=limit):
                items.append({
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
                })
            return items
            
    except Exception as e:
        log_error(f"Failed to list checkpoints: {e}")
        return []


def load_checkpoint(
    *,
    thread_id: str,
    checkpoint_id: str,
    checkpoint_ns: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Load a specific checkpoint for time-travel or state inspection.
    
    Args:
        thread_id: The thread the checkpoint belongs to
        checkpoint_id: The specific checkpoint to load
        checkpoint_ns: Namespace of the checkpoint
    
    Returns:
        Checkpoint data dictionary, or None if not found
    """
    config = build_config_payload(
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        checkpoint_ns=checkpoint_ns,
    )
    
    try:
        with checkpoint_context() as checkpointer:
            tup = checkpointer.get_tuple(config)
            
            if not tup:
                log_warning(f"Checkpoint not found: {checkpoint_id}")
                return None
            
            return {
                "config": tup.config,
                "checkpoint": tup.checkpoint,
                "metadata": tup.metadata,
                "parent_config": tup.parent_config,
                "pending_writes": tup.pending_writes,
            }
            
    except Exception as e:
        log_error(f"Failed to load checkpoint: {e}")
        return None


def delete_checkpoints(
    *,
    thread_id: str,
    checkpoint_ns: str = "",
) -> int:
    """
    Delete all checkpoints for a thread.
    
    Use with caution - this permanently removes checkpoint history.
    
    Args:
        thread_id: The thread to delete checkpoints for
        checkpoint_ns: Namespace filter
    
    Returns:
        Number of checkpoints deleted
    """
    try:
        with checkpoint_context() as checkpointer:
            config = build_config_payload(
                thread_id=thread_id,
                checkpoint_ns=checkpoint_ns,
            )
            
            # List all checkpoints first
            checkpoints = list(checkpointer.list(config, limit=1000))
            count = len(checkpoints)
            
            if count == 0:
                log_debug(f"No checkpoints to delete for thread {thread_id}")
                return 0
            
            # Try multiple delete methods for compatibility
            deleted = False
            
            # Method 1: Use delete() if available (langgraph >= 0.2)
            if hasattr(checkpointer, "delete"):
                try:
                    checkpointer.delete(config)
                    deleted = True
                    log_info(f"Deleted {count} checkpoints via delete() for thread {thread_id}")
                except Exception as e:
                    log_warning(f"delete() failed: {e}")
            
            # Method 2: Direct SQL delete as fallback
            if not deleted:
                try:
                    conn_string = get_connection_string()
                    import psycopg
                    with psycopg.connect(conn_string) as conn:
                        with conn.cursor() as cur:
                            # Delete from checkpoint tables
                            cur.execute(
                                "DELETE FROM checkpoints WHERE thread_id = %s",
                                (thread_id,)
                            )
                            cur.execute(
                                "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                                (thread_id,)
                            )
                            cur.execute(
                                "DELETE FROM checkpoint_blobs WHERE thread_id = %s",
                                (thread_id,)
                            )
                        conn.commit()
                    deleted = True
                    log_info(f"Deleted checkpoints via SQL for thread {thread_id}")
                except Exception as e:
                    log_warning(f"SQL delete failed: {e}")
            
            if not deleted:
                log_warning(f"Failed to delete checkpoints for thread {thread_id}")
                return 0
            
            return count
            
    except Exception as e:
        log_error(f"Failed to delete checkpoints: {e}")
        return 0


def get_latest_checkpoint_state(
    *,
    thread_id: str,
    checkpoint_ns: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Get the latest checkpoint state for a thread.
    
    Useful for resuming interrupted workflows.
    
    Args:
        thread_id: The thread to get the latest checkpoint for
        checkpoint_ns: Namespace filter
    
    Returns:
        The latest checkpoint state, or None if no checkpoints exist
    """
    checkpoints = list_checkpoints(
        thread_id=thread_id,
        checkpoint_ns=checkpoint_ns,
        limit=1,
    )
    
    if not checkpoints:
        return None
    
    latest = checkpoints[0]
    return load_checkpoint(
        thread_id=thread_id,
        checkpoint_id=latest["checkpoint_id"],
        checkpoint_ns=checkpoint_ns,
    )


def checkpoint_exists(
    *,
    thread_id: str,
    checkpoint_ns: str = "",
) -> bool:
    """
    Check if any checkpoints exist for a thread.
    
    Args:
        thread_id: The thread to check
        checkpoint_ns: Namespace filter
    
    Returns:
        True if at least one checkpoint exists
    """
    checkpoints = list_checkpoints(
        thread_id=thread_id,
        checkpoint_ns=checkpoint_ns,
        limit=1,
    )
    return len(checkpoints) > 0
