"""User profile model."""

from typing import Optional, List
from sqlalchemy import String, Boolean, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from models.base import Base, TimestampMixin


class UserProfile(Base, TimestampMixin):
	"""
	User profile for personal information, onboarding data, and XP tracking.

	Attributes:
		id: UUID primary key
		user_id: UUID foreign key to User
		full_name: Optional full name
		phone: Optional phone number
		address: Optional address
		company: Optional company name
		job_title: Optional job title
		locale: Optional locale
		specialization: Agent specialization chosen during onboarding
		agent_name: Custom agent name
		tone: Agent tone preference
		directives: Prime directives for the agent
		data_sources: Selected data sources (cloud, repo, local)
		onboarding_completed: Whether onboarding has been completed
		bio: User bio
		study_goal: Study goals
		xp: Experience points
		level: Current level (derived from XP)
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

	specialization: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	agent_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
	tone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
	directives: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
	data_sources: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
	onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

	bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
	study_goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

	xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
	level: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

	user = relationship("User", back_populates="profile")

	def __repr__(self) -> str:
		return f"<UserProfile(id={self.id}, user_id={self.user_id})>"
