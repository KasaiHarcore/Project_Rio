"""Document service — CRUD wrapper around DocumentRepository."""

from typing import List, Optional
from uuid import UUID

from models.document import Document, DocumentStatus
from repositories.document_repository import DocumentRepository
from utils.log import log_info


class DocumentService:
    """Service for document CRUD operations."""

    def __init__(self, document_repo: DocumentRepository) -> None:
        self._repo = document_repo

    def create_document(
        self,
        user_id: UUID,
        name: str,
        file_type: str,
        size_bytes: int,
    ) -> Document:
        """Create a new document record with PROCESSING status."""
        doc = Document(
            user_id=user_id,
            name=name,
            file_type=file_type,
            size_bytes=size_bytes,
            status=DocumentStatus.PROCESSING,
        )
        doc = self._repo.create(doc)
        log_info(f"Created document {doc.id} for user {user_id}")
        return doc

    def mark_ready(self, doc_id: UUID, user_id: UUID, chunk_count: int) -> Optional[Document]:
        """Mark a document as ready after successful ingestion."""
        doc = self._repo.find_by_id(doc_id, user_id)
        if not doc:
            return None
        doc.status = DocumentStatus.READY
        doc.chunk_count = chunk_count
        self._repo.flush()
        return doc

    def mark_error(self, doc_id: UUID, user_id: UUID, error_message: str) -> Optional[Document]:
        """Mark a document as errored after failed ingestion."""
        doc = self._repo.find_by_id(doc_id, user_id)
        if not doc:
            return None
        doc.status = DocumentStatus.ERROR
        doc.error_message = error_message[:2000]
        self._repo.flush()
        return doc

    def list_documents(self, user_id: UUID, limit: int = 50) -> List[Document]:
        """List all documents for a user."""
        return self._repo.list_by_user(user_id, limit=limit)

    def delete_document(self, doc_id: UUID, user_id: UUID) -> Optional[Document]:
        """Delete a document. Returns the document if found, None otherwise."""
        doc = self._repo.find_by_id(doc_id, user_id)
        if not doc:
            return None
        self._repo.delete(doc)
        self._repo.flush()
        log_info(f"Deleted document {doc_id} for user {user_id}")
        return doc
