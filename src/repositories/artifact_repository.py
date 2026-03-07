"""Artifact repository — data access for Artifact model."""

from typing import Optional, List
from uuid import UUID

from models.artifact import Artifact
from repositories.base import BaseRepository


class ArtifactRepository(BaseRepository):
    """Data access for Artifact entities."""

    def find_by_id(self, artifact_id: UUID, user_id: UUID) -> Optional[Artifact]:
        return (
            self.db.query(Artifact)
            .filter(Artifact.id == artifact_id, Artifact.user_id == user_id)
            .first()
        )

    def list_by_user(
        self,
        user_id: UUID,
        thread_id: Optional[UUID] = None,
        artifact_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Artifact]:
        q = self.db.query(Artifact).filter(Artifact.user_id == user_id)
        if thread_id:
            q = q.filter(Artifact.thread_id == thread_id)
        if artifact_type:
            q = q.filter(Artifact.artifact_type == artifact_type)
        return (
            q.order_by(Artifact.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def create(self, artifact: Artifact) -> Artifact:
        self.db.add(artifact)
        self.db.flush()
        return artifact

    def delete_by_id(self, artifact_id: UUID, user_id: UUID) -> int:
        return (
            self.db.query(Artifact)
            .filter(Artifact.id == artifact_id, Artifact.user_id == user_id)
            .delete()
        )
