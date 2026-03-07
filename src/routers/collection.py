"""Collection CRUD endpoints.

Provides:
    GET    /collections            – list collections (with note counts)
    POST   /collections            – create a collection
    PATCH  /collections/{id}       – rename a collection
    DELETE /collections/{id}       – delete a collection
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.dependencies import get_current_user
from services.collection_service import CollectionService
from models.user import User
from schemas.note_collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionInDB,
)

router = APIRouter(prefix="/collections", tags=["collections"])

_svc = CollectionService()


# -- List --

@router.get("", response_model=List[CollectionInDB])
def list_collections(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
):
    """List collections for the authenticated user."""
    return _svc.list_collections(user.id, limit=limit, offset=offset)


# -- Create --

@router.post("", response_model=CollectionInDB, status_code=status.HTTP_201_CREATED)
def create_collection(
    body: CollectionCreate,
    user: User = Depends(get_current_user),
):
    """Create a new collection."""
    return _svc.create_collection(user.id, body)


# -- Update --

@router.patch("/{collection_id}", response_model=CollectionInDB)
def update_collection(
    collection_id: UUID,
    body: CollectionUpdate,
    user: User = Depends(get_current_user),
):
    """Rename a collection."""
    c = _svc.update_collection(user.id, collection_id, body)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")
    return c


# -- Delete --

@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: UUID,
    user: User = Depends(get_current_user),
):
    """Delete a collection. Notes in the collection will have collection_id set to NULL."""
    deleted = _svc.delete_collection(user.id, collection_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collection not found")
