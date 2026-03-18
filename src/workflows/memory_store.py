"""
Long-Term Memory Store for Multi-Agent Workflow.

This module provides cross-thread memory persistence using LangGraph's
PostgresStore with semantic search capabilities.

Features:
- Semantic search with embeddings
- Namespaced storage (user_id, memory_type)
- Cross-thread memory retrieval
- Automatic embedding generation

Usage:
    with memory_store_context() as store:
        graph = builder.compile(checkpointer=checkpointer, store=store)
        
    # In nodes:
    def my_node(state: AgentState, *, store: BaseStore):
        memories = store.search(("user_123", "memories"), query="...", limit=5)
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Tuple

from core.settings import get_app_config
from utils.log import log_debug, log_error, log_info, log_success, log_warning
from utils.timezone import utc_now


def _normalize_conn_string(conn_string: str) -> str:
    """
    Normalize SQLAlchemy DSNs to psycopg-compatible URIs.
    
    LangGraph's PostgresStore requires standard postgresql:// URIs,
    but SQLAlchemy may use postgresql+psycopg2:// or postgresql+psycopg://.
    """
    if conn_string.startswith("postgresql+psycopg2://"):
        return conn_string.replace("postgresql+psycopg2://", "postgresql://", 1)
    if conn_string.startswith("postgresql+psycopg://"):
        return conn_string.replace("postgresql+psycopg://", "postgresql://", 1)
    return conn_string


def get_store_connection_string() -> str:
    """Get the normalized PostgreSQL connection string for the store."""
    config = get_app_config()
    return _normalize_conn_string(config.database_url)


_embeddings_cache: Dict[str, Any] = {}


def get_embeddings():
    """
    Get the embeddings model for semantic search.
    
    Uses the same HuggingFace embedding model as configured in VectorDBConfig
    (settings.py), ensuring consistency with the RAG system.
    """
    from core.settings import get_vectordb_config
    
    if "embeddings" in _embeddings_cache:
        return _embeddings_cache["embeddings"]
    
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        
        config = get_vectordb_config()
        model_name = config.embedding_model
        
        # Determine device (same logic as qdrant_tool.py)
        device = os.getenv("EMBEDDING_DEVICE")
        if not device:
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        
        log_info(f"Loading embedding model for memory store: {model_name} on {device}")
        embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
        )
        
        _embeddings_cache["embeddings"] = embeddings
        log_success(f"Memory store embeddings ready: {model_name}")
        return embeddings
        
    except Exception as e:
        log_error(f"Failed to initialize embeddings: {e}")
        return None


def get_embedding_dims() -> int:
    """
    Get the embedding dimensions for the configured model.
    
    Dynamically determines dimensions by embedding a test string,
    or uses EMBEDDING_DIM env var if set.
    """
    if "dims" in _embeddings_cache:
        return _embeddings_cache["dims"]
    
    # Check for override
    override_dim = os.getenv("EMBEDDING_DIM")
    if override_dim and override_dim.strip():
        dims = int(override_dim)
        _embeddings_cache["dims"] = dims
        log_debug(f"Using EMBEDDING_DIM override: {dims}")
        return dims
    
    # Dynamically determine from model
    embeddings = get_embeddings()
    if embeddings:
        try:
            test_embedding = embeddings.embed_query("test")
            dims = len(test_embedding)
            _embeddings_cache["dims"] = dims
            log_debug(f"Detected embedding dimensions: {dims}")
            return dims
        except Exception as e:
            log_warning(f"Failed to detect embedding dims: {e}")
    
    # Fallback for common models
    from core.settings import get_vectordb_config
    model_name = get_vectordb_config().embedding_model.lower()
    
    if "minilm" in model_name:
        return 384  # all-MiniLM-L6-v2
    elif "mpnet" in model_name:
        return 768  # all-mpnet-base-v2
    elif "e5" in model_name:
        return 1024  # e5 models
    
    return 384  # Default for MiniLM (the default model)


@contextmanager
def memory_store_context(
    enable_semantic_search: bool = True,
) -> Iterator[Any]:
    """
    Context manager that yields a PostgresStore for long-term memory.
    
    Usage:
        with memory_store_context() as store:
            graph = builder.compile(checkpointer=checkpointer, store=store)
    
    Args:
        enable_semantic_search: Whether to enable semantic search with embeddings
    
    Yields:
        PostgresStore instance configured for long-term memory
    
    Raises:
        RuntimeError: If store initialization fails
    """
    try:
        from langgraph.store.postgres import PostgresStore
        
        conn_string = get_store_connection_string()
        log_debug("Initializing PostgresStore for long-term memory")
        
        # Configure index for semantic search
        index_config = None
        if enable_semantic_search:
            embeddings = get_embeddings()
            if embeddings:
                index_config = {
                    "embed": embeddings,
                    "dims": get_embedding_dims(),
                    "fields": ["text", "content", "memory"],  # Fields to embed
                }
                log_debug(f"Semantic search enabled with {get_embedding_dims()} dims")
            else:
                log_warning("Embeddings not available, semantic search disabled")
        
        # Create store with or without indexing
        if index_config:
            with PostgresStore.from_conn_string(conn_string, index=index_config) as store:
                store.setup()
                log_success("PostgresStore with semantic search ready")
                yield store
        else:
            with PostgresStore.from_conn_string(conn_string) as store:
                store.setup()
                log_success("PostgresStore ready (no semantic search)")
                yield store
    
    except ImportError as e:
        log_error(f"langgraph-checkpoint-postgres not installed: {e}")
        raise RuntimeError(
            "PostgresStore requires langgraph-checkpoint-postgres. "
            "Install with: pip install langgraph-checkpoint-postgres"
        ) from e
    except Exception as e:
        log_error(f"Failed to initialize PostgresStore: {e}")
        raise RuntimeError(f"Memory store initialization failed: {e}") from e


def get_memory_store(enable_semantic_search: bool = True) -> Any:
    """
    Get a PostgresStore instance.
    
    Note: Caller is responsible for cleanup. Prefer memory_store_context()
    for automatic resource management.
    
    Returns:
        PostgresStore instance
    """
    try:
        from langgraph.store.postgres import PostgresStore
        
        conn_string = get_store_connection_string()
        
        index_config = None
        if enable_semantic_search:
            embeddings = get_embeddings()
            if embeddings:
                index_config = {
                    "embed": embeddings,
                    "dims": get_embedding_dims(),
                    "fields": ["text", "content", "memory"],
                }
        
        if index_config:
            store = PostgresStore.from_conn_string(conn_string, index=index_config)
        else:
            store = PostgresStore.from_conn_string(conn_string)
        
        store.setup()
        return store
    
    except Exception as e:
        log_error(f"Failed to create memory store: {e}")
        raise


class MemoryNamespace:
    """Standard namespace patterns for organizing memories."""
    
    @classmethod
    def user_memories(cls, user_id: str) -> Tuple[str, str]:
        """Namespace for user-specific memories (preferences, facts)."""
        return (user_id, "memories")

    @classmethod
    def user_preferences(cls, user_id: str) -> Tuple[str, str]:
        """Namespace for user preferences."""
        return (user_id, "preferences")

    @classmethod
    def conversation_facts(cls, user_id: str, thread_id: str) -> Tuple[str, str, str]:
        """Namespace for facts extracted from a specific conversation."""
        return (user_id, "facts", thread_id)

    @classmethod
    def agent_instructions(cls, agent_name: str = "default") -> Tuple[str, str]:
        """Namespace for procedural memory (agent instructions)."""
        return ("agent_instructions", agent_name)


def store_memory(
    store: Any,
    *,
    user_id: str,
    memory_key: str,
    text: str,
    memory_type: str = "semantic",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Store a memory in the long-term store.
    
    Args:
        store: PostgresStore instance
        user_id: User identifier
        memory_key: Unique key for this memory
        text: The memory content
        memory_type: Type of memory (semantic, episodic, procedural)
        metadata: Additional metadata
    """
    namespace = MemoryNamespace.user_memories(user_id)
    
    value = {
        "text": text,
        "memory_type": memory_type,
        "created_at": utc_now().isoformat(),
        **(metadata or {}),
    }
    
    try:
        store.put(namespace, memory_key, value)
        log_debug(f"Stored memory {memory_key} for user {user_id}")
    except Exception as e:
        log_warning(f"Failed to store memory: {e}")


def search_memories(
    store: Any,
    *,
    user_id: str,
    query: str,
    limit: int = 5,
    memory_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search for relevant memories using semantic similarity.
    
    Args:
        store: PostgresStore instance
        user_id: User identifier
        query: Search query
        limit: Maximum results to return
        memory_type: Optional filter by memory type
    
    Returns:
        List of memory items with text, score, and metadata
    """
    namespace = MemoryNamespace.user_memories(user_id)
    
    try:
        filter_dict = None
        if memory_type:
            filter_dict = {"memory_type": memory_type}
        
        items = store.search(
            namespace,
            query=query,
            limit=limit,
            filter=filter_dict,
        )
        
        results = []
        for item in items:
            results.append({
                "key": item.key,
                "text": item.value.get("text", ""),
                "score": getattr(item, "score", None),
                "memory_type": item.value.get("memory_type"),
                "metadata": {k: v for k, v in item.value.items() if k not in ("text", "memory_type")},
            })
        
        log_debug(f"Found {len(results)} memories for query: {query[:50]}...")
        return results
    
    except Exception as e:
        log_warning(f"Memory search failed: {e}")
        return []


def list_memories_by_thread(
    store: Any,
    *,
    user_id: str,
    thread_id: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Retrieve all memories associated with a specific thread.

    Uses a broad semantic query with a thread_id filter to pull every
    memory the synthesize node stored for this conversation.

    Args:
        store: PostgresStore instance
        user_id: User identifier
        thread_id: Thread UUID string
        limit: Maximum results to return

    Returns:
        List of memory dicts with key, text, memory_type, source, created_at, mode
    """
    namespace = MemoryNamespace.user_memories(user_id)

    try:
        items = store.search(
            namespace,
            query="memory",
            limit=limit,
            filter={"thread_id": thread_id},
        )

        results = []
        for item in items:
            results.append({
                "key": item.key,
                "text": item.value.get("text", ""),
                "memory_type": item.value.get("memory_type", ""),
                "source": item.value.get("source", ""),
                "created_at": item.value.get("created_at", ""),
                "mode": item.value.get("mode", ""),
            })

        log_debug(f"Found {len(results)} memories for thread {thread_id}")
        return results

    except Exception as e:
        log_warning(f"Failed to list memories for thread {thread_id}: {e}")
        return []


def get_memory(
    store: Any,
    *,
    user_id: str,
    memory_key: str,
) -> Optional[Dict[str, Any]]:
    """
    Get a specific memory by key.
    
    Args:
        store: PostgresStore instance
        user_id: User identifier
        memory_key: The memory key
    
    Returns:
        Memory value dict, or None if not found
    """
    namespace = MemoryNamespace.user_memories(user_id)
    
    try:
        item = store.get(namespace, memory_key)
        if item:
            return item.value
        return None
    except Exception as e:
        log_warning(f"Failed to get memory {memory_key}: {e}")
        return None


def delete_memory(
    store: Any,
    *,
    user_id: str,
    memory_key: str,
) -> bool:
    """
    Delete a specific memory.
    
    Args:
        store: PostgresStore instance
        user_id: User identifier
        memory_key: The memory key to delete
    
    Returns:
        True if deleted, False otherwise
    """
    namespace = MemoryNamespace.user_memories(user_id)
    
    try:
        store.delete(namespace, memory_key)
        log_debug(f"Deleted memory {memory_key} for user {user_id}")
        return True
    except Exception as e:
        log_warning(f"Failed to delete memory {memory_key}: {e}")
        return False


def format_memories_for_prompt(memories: List[Dict[str, Any]]) -> str:
    """
    Format retrieved memories for inclusion in LLM prompt.
    
    Args:
        memories: List of memory items from search_memories()
    
    Returns:
        Formatted string for prompt injection
    """
    if not memories:
        return ""
    
    parts = ["## Relevant Memories"]
    for mem in memories:
        text = mem.get("text", "")
        score = mem.get("score")
        if score is not None:
            parts.append(f"- {text} (relevance: {score:.2f})")
        else:
            parts.append(f"- {text}")
    
    return "\n".join(parts)
