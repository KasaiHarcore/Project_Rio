"""User profile repository for CRUD operations."""

from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from backend.db.models.user_profile import UserProfile
from backend.schemas.user import UserProfileUpdate
from backend.core.exceptions import DatabaseError, NotFoundError
from backend.utils.log import log_debug, log_error, log_success


class UserProfileRepository:
    """Repository for UserProfile model CRUD operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: UUID) -> Optional[UserProfile]:
        try:
            return self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        except SQLAlchemyError as e:
            log_error(f"Database error fetching user profile: {str(e)}")
            raise DatabaseError(f"Failed to fetch user profile: {str(e)}")

    def upsert(self, user_id: UUID, profile_data: UserProfileUpdate) -> UserProfile:
        try:
            profile = self.get_by_user_id(user_id)
            update_data = profile_data.model_dump(exclude_unset=True)

            if profile is None:
                profile = UserProfile(user_id=user_id, **update_data)
                self.db.add(profile)
                self.db.commit()
                self.db.refresh(profile)
                log_success(f"User profile created for user {user_id}")
                return profile

            for field, value in update_data.items():
                setattr(profile, field, value)

            self.db.commit()
            self.db.refresh(profile)
            log_success(f"User profile updated for user {user_id}")
            return profile

        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error upserting user profile: {str(e)}")
            raise DatabaseError(f"Failed to upsert user profile: {str(e)}")

    def delete_by_user_id(self, user_id: UUID) -> bool:
        try:
            profile = self.get_by_user_id(user_id)
            if not profile:
                raise NotFoundError(f"User profile for user {user_id} not found")

            self.db.delete(profile)
            self.db.commit()
            log_success(f"User profile deleted for user {user_id}")
            return True
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error deleting user profile: {str(e)}")
            raise DatabaseError(f"Failed to delete user profile: {str(e)}")