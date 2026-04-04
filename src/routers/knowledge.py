"""Knowledge-base and search endpoints.

Knowledge provides:
    POST   /knowledge/upload       - upload documents to Qdrant
    GET    /knowledge              - list documents
    DELETE /knowledge/{document_id} - delete document and vectors

Search provides:
    POST /search/documents  - RAG document search via Qdrant
    POST /search/web        - Web search via Tavily
    POST /search/extract    - Extract content from URLs via Tavily
    POST /search/graph      - Knowledge graph search via Neo4j
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from uuid import UUID

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_db, get_document_service, get_cache_service
from core.exceptions import ValidationError, NotFoundError, ExternalServiceError
from infrastructure.cache.helpers import best_effort
from infrastructure.cache.service import CacheService
from infrastructure.data_access.qdrant_tool import get_vector_db_tool
from models.document import Document
from models.user import User
from schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from services.document_service import DocumentService
from services.xp_service import award_xp
from utils.log import log_info, log_error, log_success


# ---------------------------------------------------------------------------
# Knowledge router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

_ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".json", ".csv", ".html", ".htm", ".docx"}


def _doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc.id),
        name=doc.name,
        file_type=doc.file_type,
        size_bytes=doc.size_bytes,
        chunk_count=doc.chunk_count,
        status=doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        error_message=doc.error_message,
        uploaded_at=doc.created_at.isoformat() if doc.created_at else "",
    )


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="Document file to ingest"),
    chunking_strategy: Optional[str] = Query("recursive", description="recursive | character | semantic"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    doc_svc: DocumentService = Depends(get_document_service),
    cache: CacheService = Depends(get_cache_service),
):
    """Upload a file and ingest it into the Qdrant knowledge base.

    Supported types: .txt, .md, .pdf, .json, .csv, .html, .htm, .docx
    """
    if not file.filename:
        raise ValidationError("Filename is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type: {suffix}. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
        )

    # Read file bytes
    try:
        contents = file.file.read()
    except Exception as e:
        raise ValidationError(f"Failed to read uploaded file: {e}")

    size_bytes = len(contents)
    if size_bytes == 0:
        raise ValidationError("Uploaded file is empty")

    log_info(f"[Knowledge] upload: user={user.username} file={file.filename} size={size_bytes}")

    def _query():
        # Create tracking record (status=processing)
        doc = doc_svc.create_document(
            user_id=user.id,
            name=file.filename,
            file_type=suffix.lstrip("."),
            size_bytes=size_bytes,
        )

        # Write to temp file and ingest via VectorDBTool
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=suffix, delete=False, dir=tempfile.gettempdir()
            ) as tmp:
                tmp.write(contents)
                tmp_path = tmp.name

            result_msg = get_vector_db_tool().ingest_file(
                tmp_path,
                chunking_strategy=chunking_strategy or "recursive",
                source_name=file.filename,
                metadata={
                    "document_id": str(doc.id),
                    "user_id": str(user.id),
                    "source_name": file.filename,
                },
            )

            # Parse chunk count from result message (e.g. "Successfully indexed 12 chunks ...")
            chunk_count = 0
            for word in result_msg.split():
                if word.isdigit():
                    chunk_count = int(word)
                    break

            doc_svc.mark_ready(doc.id, user.id, chunk_count)

            log_success(f"[Knowledge] ingested: doc_id={doc.id} chunks={chunk_count}")

            # Award +15 XP for uploading a document
            try:
                award_xp(db, user.id, 15, reason="document_upload")
            except Exception:
                pass  # XP failure should not block the response

            # Invalidate L2 caches
            uid_str = str(user.id)
            best_effort(cache.invalidate_dashboard, uid_str)
            best_effort(cache.invalidate_xp, uid_str)

            return DocumentUploadResponse(
                document=_doc_to_response(doc),
                message=result_msg,
            )

        except Exception as exc:
            log_error(f"[Knowledge] ingestion failed: {exc}")
            doc_svc.mark_error(doc.id, user.id, str(exc))

            payload = DocumentUploadResponse(
                success=False,
                document=_doc_to_response(doc),
                message=f"Ingestion failed: {exc}",
            ).model_dump()
            return JSONResponse(status_code=500, content=payload)

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    return await concurrency_manager.run_in_thread(_query)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    doc_svc: DocumentService = Depends(get_document_service),
):
    """List all documents uploaded by the authenticated user."""
    def _query():
        docs = doc_svc.list_documents(user.id, limit=limit)
        return DocumentListResponse(documents=[_doc_to_response(d) for d in docs])

    return await concurrency_manager.run_in_thread(_query)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    doc_svc: DocumentService = Depends(get_document_service),
    cache: CacheService = Depends(get_cache_service),
):
    """Delete a document record and purge matching vectors from Qdrant."""
    try:
        did = UUID(document_id)
    except ValueError:
        raise ValidationError("Invalid document ID")

    def _query():
        doc = doc_svc.delete_document(did, user.id)
        if not doc:
            raise NotFoundError("Document not found")

        try:
            get_vector_db_tool().delete_document_vectors(str(doc.id), user_id=str(user.id))
        except Exception as exc:
            log_error(f"[Knowledge] vector delete failed: {exc}")

        # Invalidate dashboard (document count changed)
        best_effort(cache.invalidate_dashboard, str(user.id))

    await concurrency_manager.run_in_thread(_query)
    return None


# ---------------------------------------------------------------------------
# Search router  (was search.py)
# ---------------------------------------------------------------------------

search_router = APIRouter(prefix="/search", tags=["search"])


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


@search_router.post("/documents", response_model=DocumentSearchResponse)
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


@search_router.post("/web", response_model=WebSearchResponse)
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


@search_router.post("/extract", response_model=WebExtractResponse)
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


@search_router.post("/graph", response_model=GraphSearchResponse)
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
