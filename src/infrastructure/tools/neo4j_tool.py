"""Neo4j Graph Database tool for knowledge graph operations.

Manages the full lifecycle of Neo4j graph database:
- Entity/relationship extraction from documents via LLMGraphTransformer
- Graph-based retrieval using GraphCypherQAChain
- Entity traversal and relationship discovery
- Graph cleanup and statistics

GraphDBTool.__init__()  → only store config, no connection
    │
    └── _ensure_initialized()  → lazy init on first use
            ├── _init_graph()           → Neo4jGraph connection
            ├── _init_llm()             → ChatOpenAI from project's model registry
            └── _init_transformer()     → LLMGraphTransformer for entity extraction
"""

from __future__ import annotations

import atexit
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from utils.log import log_info, log_success, log_error, log_warning
from core.settings import get_neo4j_config


class GraphDBTool:
    """Manages Neo4j knowledge graph lifecycle."""

    def __init__(self):
        self._config = get_neo4j_config()
        self._graph = None
        self._llm = None
        self._transformer = None
        self._qa_chain = None
        self._initialized = False

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        if not self._config.enabled:
            raise RuntimeError(
                "Neo4j is not enabled. Set NEO4J_ENABLED=true to use graph features."
            )
        self._init_graph()
        self._init_llm()
        self._init_transformer()
        self._initialized = True
        log_success("Neo4j GraphDBTool fully initialized")

    def _init_graph(self) -> None:
        """Initialize Neo4j graph connection."""
        from langchain_neo4j import Neo4jGraph

        log_info(f"Connecting to Neo4j at {self._config.uri}...")
        try:
            self._graph = Neo4jGraph(
                url=self._config.uri,
                username=self._config.username,
                password=self._config.password,
                database=self._config.database,
            )
            atexit.register(self._close)
            log_success("Neo4j connection established")
        except Exception as e:
            log_error(f"Failed to connect to Neo4j: {e}")
            raise

    def _close(self) -> None:
        """Clean up Neo4j driver on exit."""
        if self._graph and hasattr(self._graph, "_driver"):
            try:
                self._graph._driver.close()
            except Exception:
                pass

    def _init_llm(self) -> None:
        """Get the project's active LLM for entity extraction."""
        from infrastructure.llm import form

        model = form.SELECTED_MODEL
        if model is None:
            raise RuntimeError(
                "No LLM model selected. Ensure register_all_models() has been called."
            )
        if model.llm is None:
            model.setup()
        self._llm = model.llm
        log_info(f"Using LLM for graph transformer: {model.name}")

    def _init_transformer(self) -> None:
        """Initialize LLMGraphTransformer for entity extraction."""
        from langchain_experimental.graph_transformers import LLMGraphTransformer

        self._transformer = LLMGraphTransformer(llm=self._llm)
        log_success("LLMGraphTransformer ready")

    def _get_qa_chain(self):
        """Lazy-init the GraphCypherQAChain."""
        if self._qa_chain is None:
            from langchain_neo4j import GraphCypherQAChain

            self._graph.refresh_schema()
            self._qa_chain = GraphCypherQAChain.from_llm(
                llm=self._llm,
                graph=self._graph,
                verbose=False,
                allow_dangerous_requests=True,
            )
        return self._qa_chain

    # ── Ingestion ────────────────────────────────────────────────────────

    def extract_and_store(
        self,
        documents: List,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Extract entities/relationships from documents and store in Neo4j.

        Args:
            documents: List of LangChain Document objects (chunks).
            metadata: Optional metadata dict (should contain document_id).

        Returns:
            Summary string of extracted entities.
        """
        self._ensure_initialized()

        if not documents:
            return "No documents provided for graph extraction."

        document_id = (metadata or {}).get("document_id", "unknown")
        user_id = (metadata or {}).get("user_id")

        log_info(
            f"Extracting entities from {len(documents)} chunks "
            f"(document_id={document_id})"
        )

        try:
            # Inject document_id into each chunk's metadata for traceability
            for doc in documents:
                doc.metadata["document_id"] = document_id
                if user_id:
                    doc.metadata["user_id"] = user_id

            # Convert documents to graph documents (entity extraction)
            graph_documents = self._transformer.convert_to_graph_documents(documents)

            total_nodes = sum(len(gd.nodes) for gd in graph_documents)
            total_rels = sum(len(gd.relationships) for gd in graph_documents)

            if total_nodes == 0:
                log_warning("No entities extracted from documents")
                return "No entities found in the provided documents."

            # Store in Neo4j with source linking
            self._graph.add_graph_documents(
                graph_documents,
                include_source=True,
            )

            # Invalidate cached QA chain schema after new data
            self._qa_chain = None

            summary = (
                f"Extracted {total_nodes} entities and {total_rels} relationships "
                f"from {len(documents)} chunks (document_id={document_id})"
            )
            log_success(summary)
            return summary

        except Exception as e:
            log_error(f"Graph extraction failed: {e}")
            return f"Graph extraction error: {e}"

    # ── Retrieval ────────────────────────────────────────────────────────

    def search_graph(
        self,
        query: str,
        *,
        user_id: Optional[str] = None,
        depth: int = 2,
    ) -> str:
        """Query the knowledge graph using natural language → Cypher.

        Args:
            query: Natural language question.
            user_id: Optional user scope (unused for now, reserved).
            depth: Traversal depth hint (unused for now, reserved).

        Returns:
            Answer string from the graph.
        """
        self._ensure_initialized()

        if not query or not query.strip():
            return "No query provided."

        log_info(f"Graph search: {query[:100]}...")

        try:
            qa_chain = self._get_qa_chain()
            result = qa_chain.invoke({"query": query})
            answer = result.get("result", "")

            if not answer or answer.strip().lower() in (
                "i don't know",
                "i don't know.",
            ):
                return ""

            log_success(f"Graph search returned {len(answer)} chars")
            return answer

        except Exception as e:
            log_warning(f"Graph search failed: {e}")
            return ""

    def get_related_entities(
        self,
        entity: str,
        *,
        depth: int = 2,
    ) -> str:
        """Traverse graph to find related nodes within N hops.

        Args:
            entity: Entity name to start traversal from.
            depth: Maximum hops.

        Returns:
            Formatted string of related entities and relationships.
        """
        self._ensure_initialized()

        cypher = """
        MATCH (n)
        WHERE toLower(n.id) CONTAINS toLower($entity)
        CALL apoc.path.subgraphAll(n, {maxLevel: $depth})
        YIELD nodes, relationships
        RETURN nodes, relationships
        LIMIT 50
        """

        # Fallback query without APOC (simpler traversal)
        cypher_simple = """
        MATCH path = (n)-[*1..$depth]-(m)
        WHERE toLower(n.id) CONTAINS toLower($entity)
        RETURN DISTINCT
            n.id AS source,
            type(last(relationships(path))) AS relationship,
            m.id AS target
        LIMIT 50
        """

        try:
            # Try simple query first (no APOC dependency)
            results = self._graph.query(
                cypher_simple,
                params={"entity": entity, "depth": depth},
            )

            if not results:
                return f"No related entities found for '{entity}'."

            parts = []
            for record in results:
                source = record.get("source", "?")
                rel = record.get("relationship", "?")
                target = record.get("target", "?")
                parts.append(f"- {source} --[{rel}]--> {target}")

            return f"Related entities for '{entity}' (depth={depth}):\n" + "\n".join(
                parts
            )

        except Exception as e:
            log_warning(f"Entity traversal failed: {e}")
            return f"Entity traversal error: {e}"

    # ── Management ───────────────────────────────────────────────────────

    def get_graph_stats(self) -> Dict[str, Any]:
        """Return graph statistics (node/relationship counts)."""
        self._ensure_initialized()

        try:
            node_count = self._graph.query(
                "MATCH (n) RETURN count(n) AS count"
            )
            rel_count = self._graph.query(
                "MATCH ()-[r]->() RETURN count(r) AS count"
            )
            label_count = self._graph.query(
                "MATCH (n) RETURN DISTINCT labels(n) AS labels, count(n) AS count"
            )

            return {
                "total_nodes": node_count[0]["count"] if node_count else 0,
                "total_relationships": rel_count[0]["count"] if rel_count else 0,
                "labels": [
                    {"label": r["labels"], "count": r["count"]}
                    for r in (label_count or [])
                ],
                "uri": self._config.uri,
                "database": self._config.database,
            }
        except Exception as e:
            log_error(f"Failed to get graph stats: {e}")
            return {"error": str(e)}

    def delete_document_graph(self, document_id: str) -> int:
        """Delete all graph nodes and relationships linked to a document.

        Args:
            document_id: The document ID whose graph data should be removed.

        Returns:
            Number of deleted nodes.
        """
        self._ensure_initialized()

        log_info(f"Deleting graph data for document_id={document_id}")

        try:
            # Delete nodes that were sourced from this document
            # The include_source=True creates (:Document) nodes with source metadata
            result = self._graph.query(
                """
                MATCH (d:Document {document_id: $doc_id})
                DETACH DELETE d
                RETURN count(d) AS deleted
                """,
                params={"doc_id": document_id},
            )
            deleted = result[0]["deleted"] if result else 0

            # Also clean up any orphaned entity nodes from this document
            orphan_result = self._graph.query(
                """
                MATCH (n)
                WHERE n.document_id = $doc_id
                DETACH DELETE n
                RETURN count(n) AS deleted
                """,
                params={"doc_id": document_id},
            )
            deleted += orphan_result[0]["deleted"] if orphan_result else 0

            # Invalidate cached QA chain schema
            self._qa_chain = None

            log_success(f"Deleted {deleted} graph nodes for document_id={document_id}")
            return deleted

        except Exception as e:
            log_error(f"Failed to delete graph data: {e}")
            return 0

    def startup_check(self) -> Dict[str, Any]:
        """Health check for Neo4j (idempotent)."""
        if not self._config.enabled:
            return {"enabled": False, "status": "disabled"}
        try:
            self._ensure_initialized()
            stats = self.get_graph_stats()
            return {"enabled": True, "status": "connected", **stats}
        except Exception as e:
            return {"enabled": True, "status": "error", "error": str(e)}


# ── Singleton ────────────────────────────────────────────────────────────

_graph_db_tool_instance: Optional[GraphDBTool] = None


def get_graph_db_tool() -> GraphDBTool:
    """Lazy singleton getter for GraphDBTool."""
    global _graph_db_tool_instance
    if _graph_db_tool_instance is None:
        _graph_db_tool_instance = GraphDBTool()
    return _graph_db_tool_instance
