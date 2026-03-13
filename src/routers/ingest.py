"""Document ingestion endpoints for files and URLs.

Provides:
    POST /ingest/url  - Ingest a document from a URL into the knowledge base
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.orm import Session

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user, get_db, get_document_service, get_cache_service
from core.exceptions import ValidationError, ExternalServiceError
from infrastructure.cache.service import CacheService
from models.user import User
from schemas.document import DocumentUploadResponse, DocumentResponse
from services.document_service import DocumentService
from services.xp_service import award_xp
from infrastructure.tools.qdrant_tool import get_vector_db_tool
from utils.log import log_info, log_error, log_success

router = APIRouter(prefix="/ingest", tags=["ingest"])

_ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".json", ".csv", ".html", ".htm", ".docx"}


def _doc_to_response(doc) -> DocumentResponse:
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


class URLIngestRequest(BaseModel):
    url: str = Field(..., description="URL of the document to ingest")
    chunking_strategy: str = Field("recursive", description="recursive | character | semantic")


@router.post("/url", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def ingest_url(
    body: URLIngestRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    doc_svc: DocumentService = Depends(get_document_service),
    cache: CacheService = Depends(get_cache_service),
):
    """Download a document from a URL and ingest it into the Qdrant knowledge base.

    Supported types: .txt, .md, .pdf, .json, .csv, .html, .htm, .docx
    """

    # Validate URL
    parsed = urlparse(body.url)
    if not parsed.scheme or not parsed.netloc:
        raise ValidationError("Invalid URL")

    # Determine filename and extension from URL path
    url_path = Path(parsed.path)
    filename = url_path.name or "document.html"
    suffix = url_path.suffix.lower() if url_path.suffix else ".html"

    if suffix not in _ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type: {suffix}. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
        )

    def _query():
        import httpx

        log_info(f"[Ingest] URL: user={user.username} url={body.url}")

        # Download the file
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(body.url)
                resp.raise_for_status()
                contents = resp.content
        except httpx.HTTPStatusError as e:
            raise ExternalServiceError(f"Failed to fetch URL (HTTP {e.response.status_code})")
        except Exception as e:
            raise ExternalServiceError(f"Failed to download URL: {e}")

        size_bytes = len(contents)
        if size_bytes == 0:
            raise ValidationError("Downloaded file is empty")

        # Create tracking record
        doc = doc_svc.create_document(
            user_id=user.id,
            name=filename,
            file_type=suffix.lstrip("."),
            size_bytes=size_bytes,
        )

        # Write to temp file and ingest
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=suffix, delete=False, dir=tempfile.gettempdir()
            ) as tmp:
                tmp.write(contents)
                tmp_path = tmp.name

            result_msg = get_vector_db_tool().ingest_file(
                tmp_path,
                chunking_strategy=body.chunking_strategy,
                source_name=filename,
                metadata={
                    "document_id": str(doc.id),
                    "user_id": str(user.id),
                    "source_name": filename,
                    "source_url": body.url,
                },
            )

            chunk_count = 0
            for word in result_msg.split():
                if word.isdigit():
                    chunk_count = int(word)
                    break

            doc_svc.mark_ready(doc.id, user.id, chunk_count)
            log_success(f"[Ingest] URL ingested: doc_id={doc.id} chunks={chunk_count}")

            try:
                award_xp(db, user.id, 15, reason="document_upload")
            except Exception:
                pass

            try:
                uid_str = str(user.id)
                cache.invalidate_dashboard(uid_str)
                cache.invalidate_xp(uid_str)
            except Exception:
                pass

            return DocumentUploadResponse(
                document=_doc_to_response(doc),
                message=result_msg,
            )

        except (ValidationError, ExternalServiceError):
            raise
        except Exception as exc:
            log_error(f"[Ingest] URL ingestion failed: {exc}")
            doc_svc.mark_error(doc.id, user.id, str(exc))
            from fastapi.responses import JSONResponse
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
