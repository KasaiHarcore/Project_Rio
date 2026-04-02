"""Artifact service — CRUD operations for AI-generated files.

Handles creation, retrieval, update, deletion, and version history.
Artifacts are created by the agent during conversations or manually
by the user. Each artifact is tied to a thread and auto-deleted when
the thread is removed (CASCADE).
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from uuid import UUID

from models.artifact import Artifact
from schemas.artifact import (
    ArtifactCreate,
    ArtifactUpdate,
    ArtifactInDB,
)
from repositories.artifact_repository import ArtifactRepository
from utils.log import log_info


class ArtifactService:
    """Service for artifact CRUD operations."""

    def __init__(self, artifact_repo: ArtifactRepository) -> None:
        self._repo = artifact_repo

    def list_artifacts(
        self,
        user_id: UUID,
        thread_id: Optional[UUID] = None,
        artifact_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ArtifactInDB]:
        """List artifacts for a user, optionally filtered by thread or type."""
        rows = self._repo.list_by_user(
            user_id=user_id,
            thread_id=thread_id,
            artifact_type=artifact_type,
            limit=limit,
            offset=offset,
        )
        return [ArtifactInDB.model_validate(r) for r in rows]

    def get_artifact(self, user_id: UUID, artifact_id: UUID) -> Optional[ArtifactInDB]:
        """Get a single artifact by ID (scoped to user)."""
        row = self._repo.find_by_id(artifact_id=artifact_id, user_id=user_id)
        return ArtifactInDB.model_validate(row) if row else None

    def get_version_history(self, user_id: UUID, artifact_id: UUID) -> List[ArtifactInDB]:
        """Get the version chain for an artifact (walking parent_id)."""
        versions: List[ArtifactInDB] = []
        current_id: Optional[UUID] = artifact_id
        visited = set()
        while current_id and current_id not in visited:
            visited.add(current_id)
            row = self._repo.find_by_id(artifact_id=current_id, user_id=user_id)
            if not row:
                break
            versions.append(ArtifactInDB.model_validate(row))
            current_id = row.parent_id
        return versions

    def create_artifact(self, user_id: UUID, data: ArtifactCreate) -> ArtifactInDB:
        """Create a new artifact."""
        version = 1
        if data.parent_id:
            parent = self._repo.find_by_id(
                artifact_id=UUID(data.parent_id),
                user_id=user_id,
            )
            if parent:
                version = parent.version + 1

        artifact = Artifact(
            user_id=user_id,
            thread_id=UUID(data.thread_id) if data.thread_id else None,
            name=data.name,
            artifact_type=data.artifact_type,
            language=data.language,
            content=data.content,
            version=version,
            parent_id=UUID(data.parent_id) if data.parent_id else None,
        )
        self._repo.create(artifact)
        log_info(f"Created artifact {artifact.id} ({data.name}) for user {user_id}")
        return ArtifactInDB.model_validate(artifact)

    def create_artifacts_from_agent(
        self,
        user_id: UUID,
        artifacts_json: List[Dict[str, Any]],
        thread_id: Optional[str] = None,
    ) -> List[ArtifactInDB]:
        """Bulk-create artifacts from agent output."""
        created: List[ArtifactInDB] = []
        for a in artifacts_json[:10]:  # hard-cap
            name = str(a.get("name", "untitled")).strip()[:255]
            content = str(a.get("content", "")).strip()
            if not content:
                continue

            artifact = Artifact(
                user_id=user_id,
                thread_id=UUID(thread_id) if thread_id else None,
                name=name,
                artifact_type=str(a.get("artifact_type", "code"))[:50],
                language=str(a.get("language", ""))[:50] or None,
                content=content,
                version=1,
            )
            self._repo.create(artifact)
            created.append(ArtifactInDB.model_validate(artifact))
            log_info(f"Agent-created artifact {artifact.id}: {name}")
        return created

    def update_artifact(self, user_id: UUID, artifact_id: UUID, data: ArtifactUpdate) -> Optional[ArtifactInDB]:
        """Partially update an artifact."""
        artifact = self._repo.find_by_id(artifact_id=artifact_id, user_id=user_id)
        if not artifact:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(artifact, field, value)

        self._repo.flush()
        return ArtifactInDB.model_validate(artifact)

    def delete_artifact(self, user_id: UUID, artifact_id: UUID) -> bool:
        """Delete an artifact. Returns True if deleted."""
        deleted = self._repo.delete_by_id(artifact_id=artifact_id, user_id=user_id)
        return deleted > 0
