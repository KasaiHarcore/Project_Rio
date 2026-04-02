"""User settings model for storing user preferences and configuration."""

from typing import Optional
from sqlalchemy import String, Boolean, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from models.base import Base, TimestampMixin


class UserSettings(Base, TimestampMixin):
    """User settings for storing preferences and configuration.

    Attributes:
        id: UUID primary key
        user_id: UUID foreign key to User

        # API Keys (Encrypted)
        encrypted_openai_key: Encrypted OpenAI API key
        encrypted_openrouter_key: Encrypted OpenRouter API key
        encrypted_tavily_key: Encrypted Tavily API key
        encrypted_cohere_key: Encrypted Cohere API key

        # Phoenix Tracing
        enable_phoenix_tracing: Whether to enable Phoenix tracing
        phoenix_project: Phoenix project name

        # Model Parameters
        temperature: Model temperature for response creativity (0.0-2.0)
        max_tokens: Maximum tokens in model response
        top_p: Nucleus sampling parameter
        frequency_penalty: Frequency penalty for token repetition
        presence_penalty: Presence penalty for topic repetition

        # Agent Configuration
        system_prompt: Custom system prompt for the AI agent
        model_name: LLM model to use (e.g., gpt-4o-mini, gpt-4o)
        max_iterations: Maximum planning/reflection iterations
        top_k: Number of documents to retrieve from vector store
        enable_planner: Whether to enable multi-step planning
        enable_reflection: Whether to enable answer refinement

        # Notification Preferences
        mission_reminders: Enable mission deadline reminders
        chat_alerts: Enable chat response completion alerts
        system_updates: Enable system update announcements
        weekly_summary: Enable weekly progress summary
        error_alerts: Enable error notifications

        # Delivery Settings
        sound_enabled: Enable sound effects for notifications
        email_notifications: Enable email notifications
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

    encrypted_openai_key: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    encrypted_openrouter_key: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    encrypted_tavily_key: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    encrypted_cohere_key: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    enable_phoenix_tracing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    phoenix_project: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        default=None,
    )

    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        server_default="0.0",
    )

    max_tokens: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=None,
    )

    top_p: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=None,
    )

    frequency_penalty: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=None,
    )

    presence_penalty: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=None,
    )

    system_prompt: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        default=None,
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="gpt-4o-mini",
        server_default="gpt-4o-mini",
    )

    max_iterations: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10,
        server_default="10",
    )

    top_k: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
    )

    enable_planner: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    enable_reflection: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    enable_input_guardrail: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    enable_output_guardrail: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    mission_reminders: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    chat_alerts: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    system_updates: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    weekly_summary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    error_alerts: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    sound_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    email_notifications: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    user: Mapped["User"] = relationship("User", back_populates="settings")

    def __repr__(self) -> str:
        return f"<UserSettings(id={self.id}, user_id={self.user_id}, model={self.model_name})>"
