"""Base repository providing common data access patterns.

All repositories inherit from this class and receive a SQLAlchemy
session via __init__. No @staticmethod — every method is an instance
method that uses self.db for database access.
"""

from typing import TypeVar, Type, Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository:
    """Base class for all repositories.

    Usage:
        class UserRepository(BaseRepository):
            def find_by_email(self, email: str) -> User | None:
                return self.db.query(User).filter(User.email == email).first()
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, model: Type[T], entity_id: UUID) -> Optional[T]:
        """Get a single entity by primary key."""
        return self.db.get(model, entity_id)

    def add(self, entity: T) -> T:
        """Add an entity to the session."""
        self.db.add(entity)
        self.db.flush()
        return entity

    def add_all(self, entities: List[T]) -> List[T]:
        """Add multiple entities to the session."""
        self.db.add_all(entities)
        self.db.flush()
        return entities

    def delete(self, entity: T) -> None:
        """Delete a single entity."""
        self.db.delete(entity)

    def flush(self) -> None:
        """Flush pending changes to the database."""
        self.db.flush()

    def refresh(self, entity: T) -> T:
        """Refresh an entity from the database."""
        self.db.refresh(entity)
        return entity
