"""ToolUsage repository for CRUD operations."""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from backend.db.models.tool_usage import ToolUsage, ToolStatus
from backend.schemas.tool_usage import ToolUsageCreate, ToolUsageUpdate
from backend.core.exceptions import DatabaseError, NotFoundError
from backend.utils.log import log_info, log_error, log_debug, log_success


class ToolUsageRepository:
    """Repository for ToolUsage model CRUD operations."""

    def __init__(self, db: Session):
        """Initialize repository with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, tool_data: ToolUsageCreate, message_id: UUID) -> ToolUsage:
        """Create a new tool usage record.
        
        Args:
            tool_data: Tool usage creation data
            message_id: Message UUID
            
        Returns:
            Created tool usage instance
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Creating tool usage: {tool_data.tool_name} for message {message_id}")
            
            db_tool = ToolUsage(
                message_id=message_id,
                tool_name=tool_data.tool_name,
                status=tool_data.status,
                error_message=tool_data.error_message,
            )
            
            self.db.add(db_tool)
            self.db.commit()
            self.db.refresh(db_tool)
            
            log_success(f"Tool usage created: {db_tool.tool_name} ({db_tool.id})")
            return db_tool
            
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error creating tool usage: {str(e)}")
            raise DatabaseError(f"Failed to create tool usage: {str(e)}")

    def get_by_id(self, tool_id: UUID) -> Optional[ToolUsage]:
        """Get tool usage by ID.
        
        Args:
            tool_id: Tool usage UUID
            
        Returns:
            ToolUsage instance or None if not found
        """
        try:
            log_debug(f"Fetching tool usage by ID: {tool_id}")
            tool = self.db.query(ToolUsage).filter(ToolUsage.id == tool_id).first()
            
            return tool
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching tool usage: {str(e)}")
            raise DatabaseError(f"Failed to fetch tool usage: {str(e)}")

    def get_by_message(
        self,
        message_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[ToolUsage]:
        """Get tool usages by message.
        
        Args:
            message_id: Message UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of tool usage instances
        """
        try:
            log_debug(f"Fetching tool usages for message: {message_id}")
            
            tools = (
                self.db.query(ToolUsage)
                .filter(ToolUsage.message_id == message_id)
                .order_by(ToolUsage.created_at.asc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            log_debug(f"Found {len(tools)} tool usages")
            
            return tools
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching tool usages: {str(e)}")
            raise DatabaseError(f"Failed to fetch tool usages: {str(e)}")

    def get_by_tool_name(
        self,
        tool_name: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[ToolUsage]:
        """Get tool usages by tool name.
        
        Args:
            tool_name: Tool name
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of tool usage instances
        """
        try:
            log_debug(f"Fetching tool usages for tool: {tool_name}")
            
            tools = (
                self.db.query(ToolUsage)
                .filter(ToolUsage.tool_name == tool_name)
                .order_by(ToolUsage.created_at.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            log_debug(f"Found {len(tools)} tool usages")
            
            return tools
            
        except SQLAlchemyError as e:
            log_error(f"Database error fetching tool usages: {str(e)}")
            raise DatabaseError(f"Failed to fetch tool usages: {str(e)}")

    def update(self, tool_id: UUID, tool_data: ToolUsageUpdate) -> ToolUsage:
        """Update tool usage information.
        
        Args:
            tool_id: Tool usage UUID
            tool_data: Updated tool usage data
            
        Returns:
            Updated tool usage instance
            
        Raises:
            NotFoundError: If tool usage not found
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Updating tool usage: {tool_id}")
            
            db_tool = self.get_by_id(tool_id)
            if not db_tool:
                raise NotFoundError(f"Tool usage with ID {tool_id} not found")
            
            # Update fields
            update_data = tool_data.model_dump(exclude_unset=True)
            
            for field, value in update_data.items():
                setattr(db_tool, field, value)
            
            self.db.commit()
            self.db.refresh(db_tool)
            
            log_success(f"Tool usage updated: {db_tool.id}")
            return db_tool
            
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error updating tool usage: {str(e)}")
            raise DatabaseError(f"Failed to update tool usage: {str(e)}")

    def delete(self, tool_id: UUID) -> bool:
        """Delete tool usage by ID.
        
        Args:
            tool_id: Tool usage UUID
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            log_debug(f"Deleting tool usage: {tool_id}")
            
            db_tool = self.get_by_id(tool_id)
            if not db_tool:
                log_debug(f"Tool usage not found for deletion: {tool_id}")
                return False
            
            self.db.delete(db_tool)
            self.db.commit()
            
            log_success(f"Tool usage deleted: {tool_id}")
            return True
            
        except SQLAlchemyError as e:
            self.db.rollback()
            log_error(f"Database error deleting tool usage: {str(e)}")
            raise DatabaseError(f"Failed to delete tool usage: {str(e)}")