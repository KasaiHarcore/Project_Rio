"""Thread repository for CRUD operations."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from backend.db.models.thread import Thread, ThreadStatus
from backend.schemas.thread import ThreadCreate, ThreadUpdate
from backend.core.exceptions import DatabaseError, NotFoundError
from backend.utils.log import log_info, log_error, log_debug, log_success


class ThreadRepository:
    """Repository for Thread model CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, thread_data: ThreadCreate, user_id: UUID) -> Thread:
        """Create a new thread.
        
        Args:
            thread_data: Thread creation data
            user_id: Owner user UUID
            
        Returns:
            Created thread instance
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Creating thread for user {user_id}")
            
            db_thread = Thread(
                user_id=user_id,
                title=thread_data.title,
                status=thread_data.status,
            )
            
            self.db.add(db_thread)
            self.db.commit()
            self.db.refresh(db_thread)
            
            log_success(f"Thread created: {db_thread.id}")
            return db_thread
            
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error creating thread: {str(e)}")
            raise DatabaseError(f"Failed to create thread: {str(e)}")

    def get_by_id(self, thread_id: UUID, include_messages: bool = False) -> Optional[Thread]:
        """Get thread by ID.
        
        Args:
            thread_id: Thread UUID
            include_messages: Whether to eager load messages
            
        Returns:
            Thread instance or None if not found
        """
        try:
            log_debug(f"Fetching thread by ID: {thread_id}")
            
            query = self.db.query(Thread)
            
            if include_messages:
                query = query.options(joinedload(Thread.messages))
            
            thread = query.filter(Thread.id == thread_id).first()
            
            if thread:
                log_debug(f"Thread found: {thread.title}")
            
            return thread
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching thread: {str(e)}")
            raise DatabaseError(f"Failed to fetch thread: {str(e)}")

    def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ThreadStatus] = None,
    ) -> List[Thread]:
        """Get threads by user.
        
        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
        Returns:
            List of thread instances
        """
        try:
            log_debug(f"Fetching threads for user: {user_id}")
            
            query = self.db.query(Thread).filter(Thread.user_id == user_id)
            
            if status:
                query = query.filter(Thread.status == status)
            
            threads = (
                query.order_by(Thread.updated_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            log_debug(f"Found {len(threads)} threads")
            
            return threads
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching threads: {str(e)}")
            raise DatabaseError(f"Failed to fetch threads: {str(e)}")

    def update(self, thread_id: UUID, thread_data: ThreadUpdate) -> Thread:
        """Update thread information.
        
        Args:
            thread_id: Thread UUID
            thread_data: Updated thread data
            
        Returns:
            Updated thread instance
            
        Raises:
            NotFoundError: If thread not found
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Updating thread: {thread_id}")
            
            db_thread = self.get_by_id(thread_id)
            if not db_thread:
                raise NotFoundError(f"Thread with ID {thread_id} not found")
            
            # Update fields
            update_data = thread_data.model_dump(exclude_unset=True)
            
            for field, value in update_data.items():
                setattr(db_thread, field, value)
            
            self.db.commit()
            self.db.refresh(db_thread)
            
            log_success(f"Thread updated: {db_thread.id}")
            return db_thread
            
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error updating thread: {str(e)}")
            raise DatabaseError(f"Failed to update thread: {str(e)}")

    def archive(self, thread_id: UUID) -> Thread:
        """Archive a thread.
        
        Args:
            thread_id: Thread UUID
            
        Returns:
            Updated thread instance
        """
        return self.update(thread_id, ThreadUpdate(status=ThreadStatus.ARCHIVED))

    def delete(self, thread_id: UUID) -> bool:
        """Delete thread by ID (cascades to messages and tool usages).
        
        Args:
            thread_id: Thread UUID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Deleting thread: {thread_id}")
            
            db_thread = self.get_by_id(thread_id)
            if not db_thread:
                log_debug(f"Thread not found for deletion: {thread_id}")
                return False
            
            self.db.delete(db_thread)
            self.db.commit()
            
            log_success(f"Thread deleted: {thread_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error deleting thread: {str(e)}")
            raise DatabaseError(f"Failed to delete thread: {str(e)}")

    def count_by_user(self, user_id: UUID) -> int:
        """Count threads by user.
        
        Args:
            user_id: User UUID
            
        Returns:
            Thread count
        """
        try:
            count = self.db.query(Thread).filter(Thread.user_id == user_id).count()
            log_debug(f"Thread count for user {user_id}: {count}")
            
            return count
            
        except SQLAlchemyError as e:
            log_error(f"Database error counting threads: {str(e)}")
            raise DatabaseError(f"Failed to count threads: {str(e)}")