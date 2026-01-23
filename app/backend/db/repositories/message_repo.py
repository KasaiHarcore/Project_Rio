"""Message repository for CRUD operations."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from backend.db.models.message import Message, MessageRole
from backend.schemas.message import MessageCreate, MessageUpdate
from backend.core.exceptions import DatabaseError, NotFoundError
from backend.utils.log import log_info, log_error, log_debug, log_success


class MessageRepository:
    """Repository for Message model CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, message_data: MessageCreate, thread_id: UUID) -> Message:
        """Create a new message.
        
        Args:
            message_data: Message creation data
            thread_id: Thread UUID
            
        Returns:
            Created message instance
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Creating message for thread {thread_id}")
            
            db_message = Message(
                thread_id=thread_id,
                content=message_data.content,
                role=message_data.role,
                run_id=message_data.run_id,
            )
            
            self.db.add(db_message)
            self.db.commit()
            self.db.refresh(db_message)
            
            log_success(f"Message created: {db_message.id}")
            return db_message
            
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error creating message: {str(e)}")
            raise DatabaseError(f"Failed to create message: {str(e)}")

    def get_by_id(self, message_id: UUID) -> Optional[Message]:
        """Get message by ID.
        
        Args:
            message_id: Message UUID
            
        Returns:
            Message instance or None if not found
        """
        try:
            log_debug(f"Fetching message by ID: {message_id}")
            message = self.db.query(Message).filter(Message.id == message_id).first()
            
            return message
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching message: {str(e)}")
            raise DatabaseError(f"Failed to fetch message: {str(e)}")

    def get_by_thread(
        self,
        thread_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """Get messages by thread.
        
        Args:
            thread_id: Thread UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of message instances ordered by creation time
        """
        try:
            log_debug(f"Fetching messages for thread: {thread_id}")
            
            messages = (
                self.db.query(Message)
                .filter(Message.thread_id == thread_id)
                .order_by(Message.created_at.asc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            log_debug(f"Found {len(messages)} messages")
            
            return messages
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching messages: {str(e)}")
            raise DatabaseError(f"Failed to fetch messages: {str(e)}")

    def update(self, message_id: UUID, message_data: MessageUpdate) -> Message:
        """Update message information.
        
        Args:
            message_id: Message UUID
            message_data: Updated message data
            
        Returns:
            Updated message instance
            
        Raises:
            NotFoundError: If message not found
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Updating message: {message_id}")
            
            db_message = self.get_by_id(message_id)
            if not db_message:
                raise NotFoundError(f"Message with ID {message_id} not found")
            
            # Update fields
            update_data = message_data.model_dump(exclude_unset=True)
            
            for field, value in update_data.items():
                setattr(db_message, field, value)
            
            self.db.commit()
            self.db.refresh(db_message)
            
            log_success(f"Message updated: {db_message.id}")
            return db_message
            
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error updating message: {str(e)}")
            raise DatabaseError(f"Failed to update message: {str(e)}")

    def delete(self, message_id: UUID) -> bool:
        """Delete message by ID.
        
        Args:
            message_id: Message UUID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Deleting message: {message_id}")
            
            db_message = self.get_by_id(message_id)
            if not db_message:
                log_debug(f"Message not found for deletion: {message_id}")
                return False
            
            self.db.delete(db_message)
            self.db.commit()
            
            log_success(f"Message deleted: {message_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error deleting message: {str(e)}")
            raise DatabaseError(f"Failed to delete message: {str(e)}")

    def count_by_thread(self, thread_id: UUID) -> int:
        """Count messages by thread.
        
        Args:
            thread_id: Thread UUID
            
        Returns:
            Message count
        """
        try:
            count = self.db.query(Message).filter(Message.thread_id == thread_id).count()
            log_debug(f"Message count for thread {thread_id}: {count}")
            
            return count
            
        except SQLAlchemyError as e:
            log_error(f"Database error counting messages: {str(e)}")
            raise DatabaseError(f"Failed to count messages: {str(e)}")