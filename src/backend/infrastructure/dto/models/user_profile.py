"""User profile model."""

from typing import Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from backend.infrastructure.dto.base import Base, TimestampMixin


class UserProfile(Base, TimestampMixin):
	"""
	User profile for optional personal information.
 
	Attributes:
		id: UUID primary key
		user_id: UUID foreign key to User
		full_name: Optional full name
		phone: Optional phone number
		address: Optional address
		company: Optional company name
		job_title: Optional job title
		locale: Optional locale
	"""

	id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		primary_key=True,
		default=uuid.uuid4,
		index=True,
	)

	user_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("user.id", ondelete="CASCADE"),
		nullable=False,
		unique=True,
		index=True,
	)

	full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
	phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
	company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
	job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
	locale: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

	user = relationship("User", back_populates="profile")

	def __repr__(self) -> str:
		return f"<UserProfile(id={self.id}, user_id={self.user_id})>"
