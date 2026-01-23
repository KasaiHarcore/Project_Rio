"""User repository for CRUD operations and lookups."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from backend.db.models.user import User
from backend.schemas.user import UserCreate, UserUpdate
from backend.security.auth import get_password_hash
from backend.core.exceptions import DatabaseError, DuplicateError, NotFoundError
from backend.utils.log import log_info, log_error, log_debug, log_success


class UserRepository:
    """Repository for User model CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, user_data: UserCreate) -> User:
        """Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created user instance
            
        Raises:
            DuplicateError: If user with email/username already exists
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Creating user with email: {user_data.email}")
            
            # Hash password
            hashed_password = get_password_hash(user_data.password)
            
            # Create user instance
            db_user = User(
                email=user_data.email,
                username=user_data.username,
                hashed_password=hashed_password,
                role=user_data.role,
            )
            
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            
            log_success(f"User created: {db_user.email} (ID: {db_user.id})")
            return db_user
            
        except IntegrityError as e:
            self.db.rollback()
            log_error(f"Duplicate user: {str(e)}")
            raise DuplicateError(f"User with email or username already exists")
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error creating user: {str(e)}")
            raise DatabaseError(f"Failed to create user: {str(e)}")

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User instance or None if not found
        """
        try:
            log_debug(f"Fetching user by ID: {user_id}")
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if user:
                log_debug(f"User found: {user.email}")
            else:
                log_debug(f"User not found with ID: {user_id}")
            
            return user
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching user: {str(e)}")
            raise DatabaseError(f"Failed to fetch user: {str(e)}")

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email.
        
        Args:
            email: User email
            
        Returns:
            User instance or None if not found
        """
        try:
            log_debug(f"Fetching user by email: {email}")
            user = self.db.query(User).filter(User.email == email).first()
            
            if user:
                log_debug(f"User found: {user.username}")
            else:
                log_debug(f"User not found with email: {email}")
            
            return user
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching user: {str(e)}")
            raise DatabaseError(f"Failed to fetch user: {str(e)}")

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username.
        
        Args:
            username: Username
            
        Returns:
            User instance or None if not found
        """
        try:
            log_debug(f"Fetching user by username: {username}")
            user = self.db.query(User).filter(User.username == username).first()
            
            if user:
                log_debug(f"User found: {user.email}")
            else:
                log_debug(f"User not found with username: {username}")
            
            return user
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching user: {str(e)}")
            raise DatabaseError(f"Failed to fetch user: {str(e)}")

    def get_multi(
        self, skip: int = 0, limit: int = 100, active_only: bool = False
    ) -> List[User]:
        """Get multiple users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            active_only: If True, only return active users
            
        Returns:
            List of user instances
        """
        try:
            log_debug(f"Fetching users (skip={skip}, limit={limit}, active_only={active_only})")
            
            query = self.db.query(User)
            
            users = query.offset(skip).limit(limit).all()
            log_debug(f"Found {len(users)} users")
            
            return users
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching users: {str(e)}")
            raise DatabaseError(f"Failed to fetch users: {str(e)}")

    def update(self, user_id: UUID, user_data: UserUpdate) -> User:
        """Update user information.
        
        Args:
            user_id: User ID
            user_data: Updated user data
            
        Returns:
            Updated user instance
            
        Raises:
            NotFoundError: If user not found
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Updating user: {user_id}")
            
            db_user = self.get_by_id(user_id)
            if not db_user:
                raise NotFoundError(f"User with ID {user_id} not found")
            
            # Update fields
            update_data = user_data.model_dump(exclude_unset=True)
            
            # Handle password hashing if password is being updated
            if "password" in update_data:
                update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
            
            for field, value in update_data.items():
                setattr(db_user, field, value)
            
            self.db.commit()
            self.db.refresh(db_user)
            
            log_success(f"User updated: {db_user.email} (ID: {db_user.id})")
            return db_user
            
        except NotFoundError:
            raise
        except IntegrityError as e:
            self.db.rollback()
            log_error(f"Duplicate user data: {str(e)}")
            raise DuplicateError(f"User with email or username already exists")
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error updating user: {str(e)}")
            raise DatabaseError(f"Failed to update user: {str(e)}")

    def delete(self, user_id: UUID) -> bool:
        """Delete user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Deleting user: {user_id}")
            
            db_user = self.get_by_id(user_id)
            if not db_user:
                log_debug(f"User not found for deletion: {user_id}")
                return False
            
            self.db.delete(db_user)
            self.db.commit()
            
            log_success(f"User deleted: {user_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error deleting user: {str(e)}")
            raise DatabaseError(f"Failed to delete user: {str(e)}")

    def count(self, active_only: bool = False) -> int:
        """Count total users.
        
        Args:
            active_only: If True, only count active users
            
        Returns:
            Total user count
        """
        try:
            query = self.db.query(User)
            
            count = query.count()
            log_debug(f"User count: {count} (active_only={active_only})")
            
            return count
            
        except SQLAlchemyError as e:
            log_error(f"Database error counting users: {str(e)}")
            raise DatabaseError(f"Failed to count users: {str(e)}")
