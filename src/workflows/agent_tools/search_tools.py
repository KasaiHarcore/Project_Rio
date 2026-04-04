"""ReAct tools for document retrieval, web search, and knowledge graph.

Wraps VectorDBTool, WebSearchTool, and GraphDBTool as @tool functions.
"""

from __future__ import annotations

import json
from typing import List, Optional

from langchain_core.tools import tool

from utils.log import log_info, log_warning


def build_search_tools(user_id: str) -> list:
    """Build search tools with user_id baked into closures."""

    @tool
    def search_documents(query: str, k: int = 5) -> str:
        """Search internal documents and knowledge base using semantic similarity.

        Use this tool to find information from uploaded documents, files,
        and ingested content. Returns relevant passages with source citations.

        Args:
            query: Natural language search query.
            k: Number of results to return (default 5).

        Returns:
            Formatted search results with source references and relevance scores.
        """
        from infrastructure.data_access.qdrant_tool import get_vector_db_tool

        vdb = get_vector_db_tool()
        return vdb.search_documents(query, k=k, user_id=user_id)

    @tool
    def web_search(
        query: str,
        max_results: int = 5,
        topic: str = "general",
        search_depth: str = "basic",
        start_date: str = "",
        end_date: str = "",
    ) -> str:
        """Search the internet for current information.

        Use this tool when you need up-to-date information, external facts,
        or anything not available in internal documents.

        Args:
            query: Search query (keep concise, under 12 words is ideal).
            max_results: Number of results (1-10, default 5).
            topic: Search topic — "general" or "news".
            search_depth: "basic" for fast results, "advanced" for deeper search,
                "fast" for lower latency, "ultra-fast" for minimum latency.
            start_date: Optional start date filter (YYYY-MM-DD format).
            end_date: Optional end date filter (YYYY-MM-DD format).

        Returns:
            JSON with search results including title, URL, content snippet,
            and relevance score. May include a quick answer summary.
        """
        from infrastructure.data_access.web_search_tool import web_search_tool

        result = web_search_tool.search(
            query=query,
            max_results=min(max_results, 10),
            topic=topic,
            search_depth=search_depth,
            include_answer=True,
            start_date=start_date or None,
            end_date=end_date or None,
        )
        return json.dumps(result, default=str)

    @tool
    def web_extract(
        urls: list[str],
        extract_depth: str = "basic",
        query: str = "",
    ) -> str:
        """Extract full content from one or more web page URLs.

        Use this tool AFTER web_search when you need the full text of a page,
        or when Sensei provides specific URLs to read. Returns cleaned
        markdown content from each URL.

        Args:
            urls: List of URLs to extract content from (max 5).
            extract_depth: "basic" for fast text, "advanced" for tables/embedded content.
            query: Optional — focus extraction on content relevant to this query.

        Returns:
            JSON with extracted markdown content for each URL, plus any failed URLs.
        """
        from infrastructure.data_access.web_extract_tool import web_extract_tool

        result = web_extract_tool.extract(
            urls=urls[:5],
            extract_depth=extract_depth if extract_depth in ("basic", "advanced") else "basic",
            query=query or None,
        )
        return json.dumps(result, default=str)

    tools = [search_documents, web_search, web_extract]

    # Only add graph search if Neo4j is enabled
    try:
        from core.settings import get_neo4j_config

        neo4j_cfg = get_neo4j_config()
        if neo4j_cfg.get("enabled"):

            @tool
            def search_knowledge_graph(query: str, depth: int = 2) -> str:
                """Search the knowledge graph for entity relationships.

                Use this tool when you need to find connections between concepts,
                entities, or topics stored in the knowledge graph.

                Args:
                    query: Natural language question about entities/relationships.
                    depth: Traversal depth for related entity lookup (default 2).

                Returns:
                    Answer from graph traversal, or related entities and relationships.
                """
                from infrastructure.data_access.neo4j_tool import get_graph_db_tool

                graph_tool = get_graph_db_tool()
                answer = graph_tool.search_graph(query, user_id=user_id, depth=depth)
                if answer:
                    return answer
                # Fallback: try entity traversal from the query
                return graph_tool.get_related_entities(query, depth=depth)

            tools.append(search_knowledge_graph)
    except Exception:
        pass

    return tools
