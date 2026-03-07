"""Knowledge-base endpoints: upload documents, list, delete.

Files are ingested into the Qdrant vector store via the existing
IngestionService and tracked in the ``document`` PostgreSQL table so
the frontend can list / manage them.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID

from core.dependencies import get_current_user, get_db
from models.document import Document, DocumentStatus
from models.user import User
from schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from services.xp_service import award_xp
from infrastructure.tools.qdrant_tool import get_vector_db_tool
from utils.log import log_info, log_error, log_success


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ── Helpers ─────────────────────────────────────────────────────────────────

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


# ── Upload ──────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(..., description="Document file to ingest"),
    chunking_strategy: Optional[str] = Query("recursive", description="recursive | character | semantic"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a file and ingest it into the Qdrant knowledge base.

    Supported types: .txt, .md, .pdf, .json, .csv, .html, .htm, .docx
    """
    if not file.filename:
        raise HTTPException(status_code=422, detail="Filename is required")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}",
        )

    # Read file bytes
    try:
        contents = file.file.read()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to read uploaded file: {e}")

    size_bytes = len(contents)
    if size_bytes == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    log_info(f"[Knowledge] upload: user={user.username} file={file.filename} size={size_bytes}")

    # Create tracking record (status=processing)
    doc = Document(
        user_id=user.id,
        name=file.filename,
        file_type=suffix.lstrip("."),
        size_bytes=size_bytes,
        status=DocumentStatus.PROCESSING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

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

        # Parse chunk count from result message (e.g. "Successfully indexed 12 chunks …")
        chunk_count = 0
        for word in result_msg.split():
            if word.isdigit():
                chunk_count = int(word)
                break

        doc.status = DocumentStatus.READY
        doc.chunk_count = chunk_count
        db.commit()
        db.refresh(doc)

        log_success(f"[Knowledge] ingested: doc_id={doc.id} chunks={chunk_count}")

        # Award +15 XP for uploading a document
        try:
            award_xp(db, user.id, 15, reason="document_upload")
        except Exception:
            pass  # XP failure should not block the response

        # Invalidate L2 caches
        try:
            from infrastructure.cache import cache_service
            uid_str = str(user.id)
            cache_service.invalidate_dashboard(uid_str)
            cache_service.invalidate_xp(uid_str)
        except Exception:
            pass

        return DocumentUploadResponse(
            document=_doc_to_response(doc),
            message=result_msg,
        )

    except Exception as exc:
        log_error(f"[Knowledge] ingestion failed: {exc}")
        doc.status = DocumentStatus.ERROR
        doc.error_message = str(exc)[:2000]
        db.commit()
        db.refresh(doc)

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


# ── List documents ──────────────────────────────────────────────────────────

@router.get("", response_model=DocumentListResponse)
def list_documents(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all documents uploaded by the authenticated user."""
    docs = (
        db.query(Document)
        .filter(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
        .limit(limit)
        .all()
    )
    return DocumentListResponse(documents=[_doc_to_response(d) for d in docs])


# ── Delete document ─────────────────────────────────────────────────────────

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document record and purge matching vectors from Qdrant."""
    try:
        did = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    doc = db.query(Document).filter(Document.id == did, Document.user_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        get_vector_db_tool().delete_document_vectors(str(doc.id), user_id=str(user.id))
    except Exception as exc:
        log_error(f"[Knowledge] vector delete failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to remove document from vector store")

    db.delete(doc)
    db.commit()

    # Invalidate dashboard (document count changed)
    try:
        from infrastructure.cache import cache_service
        cache_service.invalidate_dashboard(str(user.id))
    except Exception:
        pass

    return None
