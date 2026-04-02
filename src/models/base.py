"""SQLAlchemy Base Class and Metadata Registry.

This module provides:
- Base declarative class for all ORM models
- Naming conventions for database constraints
- Common mixins for timestamps and soft delete

Naming Convention:
    - Indexes: ix_<column_label>
    - Unique: uq_<table>_<column>
    - Check: ck_<table>_<constraint>
    - Foreign Key: fk_<table>_<column>_<referred_table>
    - Primary Key: pk_<table>
"""

import re
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Naming convention for database constraints
# This ensures consistent naming across all migrations
CONVENTION: Dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=CONVENTION)


class Base(DeclarativeBase):
    """Base class for all database models.
    
    Features:
    - Auto-generated table names from class names (CamelCase -> snake_case)
    - Consistent constraint naming via metadata
    - Built-in dict() method for serialization
    """

    metadata = metadata

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name.
        
        Converts CamelCase to snake_case:
            UserProfile -> user_profile
            AuditLog -> audit_log
        """
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()
        return name

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary.
        
        Returns:
            Dictionary with column names as keys and values.
        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
    
    # Alias for backward compatibility
    dict = to_dict


class TimestampMixin:
    """Mixin for automatic created_at and updated_at timestamps.
    
    Usage:
        class MyModel(Base, TimestampMixin):
            id: Mapped[int] = mapped_column(primary_key=True)
            name: Mapped[str]
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="Timestamp when record was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="Timestamp when record was last updated",
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality.
    
    Usage:
        class MyModel(Base, SoftDeleteMixin):
            id: Mapped[int] = mapped_column(primary_key=True)
            
        # Soft delete
        record.deleted_at = datetime.utcnow()
        
        # Query non-deleted
        db.query(MyModel).filter(MyModel.deleted_at.is_(None))
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        doc="Timestamp when record was soft deleted (None = active)",
    )