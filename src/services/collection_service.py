"""Collection service — CRUD operations for note collections.

Handles creation, retrieval, update, and deletion of note collections.
Collections provide folder-like organization for notes.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from models.note_collection import NoteCollection
from schemas.note_collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionInDB,
)
from repositories.collection_repository import CollectionRepository
from utils.log import log_info


class CollectionService:
    """Service for note collection CRUD operations."""

    def __init__(self, collection_repo: CollectionRepository) -> None:
        self._repo = collection_repo

    # -- Read --

    def list_collections(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CollectionInDB]:
        """List collections for a user with note counts."""
        rows = self._repo.list_by_user(user_id=user_id, limit=limit, offset=offset)
        count_map = self._repo.get_note_counts(user_id=user_id)

        result = []
        for col in rows:
            data = CollectionInDB.model_validate(col)
            data.note_count = count_map.get(col.id, 0)
            result.append(data)
        return result

    def get_collection(self, user_id: UUID, collection_id: UUID) -> Optional[CollectionInDB]:
        """Get a single collection by ID."""
        row = self._repo.find_by_id(collection_id=collection_id, user_id=user_id)
        if not row:
            return None

        count = self._repo.count_notes_in(collection_id=collection_id, user_id=user_id)
        data = CollectionInDB.model_validate(row)
        data.note_count = count
        return data

    # -- Create --

    def create_collection(self, user_id: UUID, data: CollectionCreate) -> CollectionInDB:
        """Create a new collection."""
        col = NoteCollection(
            user_id=user_id,
            name=data.name,
        )
        self._repo.create(col)
        log_info(f"Created collection {col.id} for user {user_id}")
        result = CollectionInDB.model_validate(col)
        result.note_count = 0
        return result

    # -- Update --

    def update_collection(
        self,
        user_id: UUID,
        collection_id: UUID,
        data: CollectionUpdate,
    ) -> Optional[CollectionInDB]:
        """Partially update a collection."""
        col = self._repo.find_by_id(collection_id=collection_id, user_id=user_id)
        if not col:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(col, field, value)

        self._repo.flush()

        count = self._repo.count_notes_in(collection_id=collection_id, user_id=user_id)
        result = CollectionInDB.model_validate(col)
        result.note_count = count
        return result

    # -- Delete --

    def delete_collection(self, user_id: UUID, collection_id: UUID) -> bool:
        """Delete a collection. Notes in it get collection_id set to NULL (via FK SET NULL)."""
        deleted = self._repo.delete_by_id(collection_id=collection_id, user_id=user_id)
        return deleted > 0
