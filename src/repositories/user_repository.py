"""User repository — data access for User model."""

from typing import Optional
from uuid import UUID

from sqlalchemy import exists, func
from sqlalchemy.orm import Session

from models.user import User
from repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Data access for User entities."""

    def find_by_id(self, user_id: UUID) -> Optional[User]:
        return self.db.get(User, user_id)

    def find_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def find_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def find_by_username_or_email(self, identifier: str) -> Optional[User]:
        """Find user by username first, then email."""
        user = self.find_by_username(identifier)
        if not user:
            user = self.find_by_email(identifier)
        return user

    def find_by_oauth(self, provider: str, oauth_id: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.auth_provider == provider, User.oauth_id == oauth_id)
            .first()
        )

    def username_exists(self, username: str, exclude_id: Optional[UUID] = None) -> bool:
        q = self.db.query(func.count(User.id)).filter(User.username == username)
        if exclude_id:
            q = q.filter(User.id != exclude_id)
        return (q.scalar() or 0) > 0

    def email_exists(self, email: str, exclude_id: Optional[UUID] = None) -> bool:
        q = self.db.query(func.count(User.id)).filter(User.email == email)
        if exclude_id:
            q = q.filter(User.id != exclude_id)
        return (q.scalar() or 0) > 0

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user
