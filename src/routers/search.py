"""Search and retrieval endpoints (RAG, web, graph).

Provides:
    POST /search/documents  - RAG document search via Qdrant
    POST /search/web        - Web search via Tavily
    POST /search/graph      - Knowledge graph search via Neo4j
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user
from core.exceptions import ValidationError, ExternalServiceError
from models.user import User
from utils.log import log_info, log_error

router = APIRouter(prefix="/search", tags=["search"])



class DocumentSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    k: int = Field(10, ge=1, le=50, description="Number of results to return")


class DocumentSearchResponse(BaseModel):
    query: str
    results: str = Field(..., description="Formatted search results from the knowledge base")


class WebSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Web search query")
    max_results: int = Field(5, ge=1, le=20, description="Maximum number of results")
    topic: str = Field("general", description="Topic: general or news")
    time_range: Optional[str] = Field(None, description="Time range filter: day, week, month, year")


class WebSearchResponse(BaseModel):
    query: str
    results: Dict[str, Any] = Field(default_factory=dict, description="Web search results")


class WebExtractRequest(BaseModel):
    urls: List[str] = Field(..., min_length=1, max_length=5, description="URLs to extract content from")
    extract_depth: Literal["basic", "advanced"] = Field("basic", description="Extraction depth: basic or advanced")
    query: Optional[str] = Field(None, description="Optional query to focus extraction on relevant content")


class WebExtractResponse(BaseModel):
    results: Dict[str, Any] = Field(default_factory=dict, description="Extraction results")


class GraphSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language query for the knowledge graph")


class GraphSearchResponse(BaseModel):
    query: str
    answer: str = Field(..., description="Answer from the knowledge graph")


@router.post("/documents", response_model=DocumentSearchResponse)
async def search_documents(
    body: DocumentSearchRequest,
    user: User = Depends(get_current_user),
):
    """Search the user's uploaded knowledge base via Qdrant vector similarity."""

    def _query():
        from infrastructure.data_access.qdrant_tool import get_vector_db_tool

        log_info(f"[Search] documents: user={user.username} query={body.query[:80]}")

        try:
            results = get_vector_db_tool().search_documents(
                body.query,
                k=body.k,
                user_id=str(user.id),
            )
        except RuntimeError as e:
            raise ExternalServiceError(f"Vector search unavailable: {e}")

        return DocumentSearchResponse(query=body.query, results=results)

    return await concurrency_manager.run_in_thread(_query)



@router.post("/web", response_model=WebSearchResponse)
async def search_web(
    body: WebSearchRequest,
    user: User = Depends(get_current_user),
):
    """Perform a web search via Tavily and return structured results."""

    def _query():
        from infrastructure.data_access.web_search_tool import web_search_tool

        log_info(f"[Search] web: user={user.username} query={body.query[:80]}")

        try:
            results = web_search_tool.search(
                query=body.query,
                max_results=body.max_results,
                topic=body.topic,
                time_range=body.time_range,
            )
        except Exception as e:
            log_error(f"[Search] web search failed: {e}")
            raise ExternalServiceError(f"Web search failed: {e}")

        return WebSearchResponse(query=body.query, results=results)

    return await concurrency_manager.run_in_thread(_query)



@router.post("/extract", response_model=WebExtractResponse)
async def extract_web(
    body: WebExtractRequest,
    user: User = Depends(get_current_user),
):
    """Extract full page content from one or more URLs via Tavily Extract."""

    def _query():
        from infrastructure.data_access.web_extract_tool import web_extract_tool

        log_info(f"[Search] extract: user={user.username} urls={len(body.urls)}")

        if not body.urls:
            raise ValidationError("At least one URL is required")

        try:
            results = web_extract_tool.extract(
                urls=body.urls,
                extract_depth=body.extract_depth,
                query=body.query,
            )
        except Exception as e:
            log_error(f"[Search] extract failed: {e}")
            raise ExternalServiceError(f"Web extract failed: {e}")

        return WebExtractResponse(results=results)

    return await concurrency_manager.run_in_thread(_query)



@router.post("/graph", response_model=GraphSearchResponse)
async def search_graph(
    body: GraphSearchRequest,
    user: User = Depends(get_current_user),
):
    """Query the Neo4j knowledge graph using natural language."""

    def _query():
        from infrastructure.data_access.neo4j_tool import get_graph_db_tool

        log_info(f"[Search] graph: user={user.username} query={body.query[:80]}")

        try:
            answer = get_graph_db_tool().search_graph(
                query=body.query,
                user_id=str(user.id),
            )
        except Exception as e:
            log_error(f"[Search] graph search failed: {e}")
            raise ExternalServiceError(f"Graph search failed: {e}")

        return GraphSearchResponse(query=body.query, answer=answer)

    return await concurrency_manager.run_in_thread(_query)
