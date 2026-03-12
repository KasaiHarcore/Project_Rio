"""GraphRAG Fusion — merges Qdrant vector results with Neo4j graph results.

When Neo4j is enabled, both systems are queried in parallel:
  query ──┬── Qdrant search (semantic) ──┐
          └── Neo4j search (graph)  ─────┤
                                         ▼
                                   Fuse results → LLM synthesis

If Neo4j is disabled or unavailable, falls back to Qdrant-only results.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from utils.log import log_info, log_success, log_warning


class GraphRAGService:
    """Fuses Qdrant vector results with Neo4j graph results."""

    def __init__(self, vector_db_tool, graph_db_tool):
        self._vector_db = vector_db_tool
        self._graph_db = graph_db_tool

    def hybrid_search(
        self,
        query: str,
        *,
        k: int = 10,
        user_id: Optional[str] = None,
    ) -> str:
        """Run Qdrant + Neo4j searches in parallel, merge results.

        Args:
            query: Search query text.
            k: Number of vector results.
            user_id: Tenant scope for vector search.

        Returns:
            Merged context string for LLM synthesis.
        """
        log_info(f"GraphRAG hybrid search: {query[:100]}...")

        vector_results = ""
        graph_results = ""

        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="graphrag") as pool:
            futures = {}

            # Always query Qdrant
            futures["vector"] = pool.submit(
                self._vector_db.search_documents,
                query=query,
                k=k,
                user_id=user_id,
            )

            # Query Neo4j if enabled and initialized
            if self._graph_db and self._graph_db.enabled:
                futures["graph"] = pool.submit(
                    self._graph_db.search_graph,
                    query,
                    user_id=user_id,
                )

            for key, future in futures.items():
                try:
                    result = future.result(timeout=30)
                    if key == "vector":
                        vector_results = result or ""
                    elif key == "graph":
                        graph_results = result or ""
                except Exception as e:
                    log_warning(f"{key} search failed in hybrid: {e}")

        merged = self._merge_results(vector_results, graph_results)
        log_success(f"GraphRAG fusion complete: {len(merged)} chars")
        return merged

    def _merge_results(self, vector_results: str, graph_results: str) -> str:
        """Combine and format results from both sources.

        Args:
            vector_results: Formatted results from Qdrant.
            graph_results: Answer string from Neo4j graph search.

        Returns:
            Combined context string.
        """
        parts = []

        if vector_results and vector_results != "No relevant documents found in the knowledge base.":
            parts.append("## Vector Search Results\n\n" + vector_results)

        if graph_results:
            parts.append(
                "## Knowledge Graph Insights\n\n"
                "The following information was derived from entity relationships "
                "in the knowledge graph:\n\n" + graph_results
            )

        if not parts:
            return "No relevant documents found in the knowledge base."

        return "\n\n---\n\n".join(parts)
