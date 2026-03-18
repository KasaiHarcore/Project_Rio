"""Pydantic Schemas for UserSettings Model.

Schemas:
    - UserSettingsBase: Common settings fields
    - UserSettingsUpdate: Partial update payload
    - UserSettingsInDB: Full settings with DB fields
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class UserSettingsBase(BaseModel):
    """Base user settings schema."""

    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Model temperature for response creativity (0.0-2.0)"
    )
    max_tokens: Optional[int] = Field(
        None,
        ge=1,
        le=100000,
        description="Maximum tokens in model response"
    )
    top_p: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )
    frequency_penalty: Optional[float] = Field(
        None,
        ge=-2.0,
        le=2.0,
        description="Frequency penalty for token repetition"
    )
    presence_penalty: Optional[float] = Field(
        None,
        ge=-2.0,
        le=2.0,
        description="Presence penalty for topic repetition"
    )

    system_prompt: Optional[str] = Field(
        None,
        description="Custom system prompt for the AI agent",
        max_length=5000
    )
    model_name: str = Field(
        default="gpt-4o-mini",
        description="LLM model to use",
        max_length=100
    )
    max_iterations: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum planning/reflection iterations"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of documents to retrieve"
    )
    enable_planner: bool = Field(
        default=True,
        description="Enable multi-step planning"
    )
    enable_reflection: bool = Field(
        default=True,
        description="Enable answer refinement"
    )
    enable_input_guardrail: bool = Field(
        default=False,
        description="Enable input guardrail (content safety check on user messages)"
    )
    enable_output_guardrail: bool = Field(
        default=False,
        description="Enable output guardrail (content safety check on AI responses)"
    )

    enable_langsmith_tracing: bool = Field(
        default=False,
        description="Enable LangSmith tracing for workflow observability"
    )
    langsmith_project: Optional[str] = Field(
        None,
        description="LangSmith project name",
        max_length=200
    )

    mission_reminders: bool = Field(
        default=True,
        description="Enable mission deadline reminders"
    )
    chat_alerts: bool = Field(
        default=True,
        description="Enable chat response completion alerts"
    )
    system_updates: bool = Field(
        default=False,
        description="Enable system update announcements"
    )
    weekly_summary: bool = Field(
        default=True,
        description="Enable weekly progress summary"
    )
    error_alerts: bool = Field(
        default=True,
        description="Enable error notifications"
    )

    sound_enabled: bool = Field(
        default=False,
        description="Enable sound effects"
    )
    email_notifications: bool = Field(
        default=False,
        description="Enable email notifications"
    )


class UserSettingsUpdate(BaseModel):
    """Schema for updating user settings (all fields optional)."""

    openai_api_key: Optional[str] = Field(
        None,
        description="OpenAI API key (will be encrypted)"
    )
    openrouter_api_key: Optional[str] = Field(
        None,
        description="OpenRouter API key (will be encrypted)"
    )
    tavily_api_key: Optional[str] = Field(
        None,
        description="Tavily API key (will be encrypted)"
    )
    cohere_api_key: Optional[str] = Field(
        None,
        description="Cohere API key (will be encrypted)"
    )
    langsmith_api_key: Optional[str] = Field(
        None,
        description="LangSmith API key (will be encrypted)"
    )

    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=100000)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)

    system_prompt: Optional[str] = Field(None, max_length=5000)
    model_name: Optional[str] = Field(None, max_length=100)
    max_iterations: Optional[int] = Field(None, ge=1, le=50)
    top_k: Optional[int] = Field(None, ge=1, le=20)
    enable_planner: Optional[bool] = None
    enable_reflection: Optional[bool] = None
    enable_input_guardrail: Optional[bool] = None
    enable_output_guardrail: Optional[bool] = None
    enable_langsmith_tracing: Optional[bool] = None
    langsmith_project: Optional[str] = Field(None, max_length=200)

    mission_reminders: Optional[bool] = None
    chat_alerts: Optional[bool] = None
    system_updates: Optional[bool] = None
    weekly_summary: Optional[bool] = None
    error_alerts: Optional[bool] = None

    sound_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None


class UserSettingsAPIStatus(BaseModel):
    """Schema for API key configuration status (never exposes actual keys)."""

    openai_configured: bool = Field(
        ...,
        description="Whether OpenAI API key is configured"
    )
    openrouter_configured: bool = Field(
        ...,
        description="Whether OpenRouter API key is configured"
    )
    tavily_configured: bool = Field(
        ...,
        description="Whether Tavily API key is configured"
    )
    cohere_configured: bool = Field(
        ...,
        description="Whether Cohere API key is configured"
    )
    langsmith_configured: bool = Field(
        ...,
        description="Whether LangSmith API key is configured"
    )
    openai_masked: Optional[str] = Field(
        None,
        description="Masked OpenAI key (e.g., 'sk-...xyz1')"
    )
    openrouter_masked: Optional[str] = Field(
        None,
        description="Masked OpenRouter key"
    )
    tavily_masked: Optional[str] = Field(
        None,
        description="Masked Tavily key"
    )
    cohere_masked: Optional[str] = Field(
        None,
        description="Masked Cohere key"
    )
    langsmith_masked: Optional[str] = Field(
        None,
        description="Masked LangSmith key"
    )


class UserSettingsInDB(UserSettingsBase):
    """Schema for user settings stored in database (NEVER includes actual API keys)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Settings UUID")
    user_id: UUID = Field(..., description="User UUID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    api_keys: Optional[UserSettingsAPIStatus] = Field(
        None,
        description="API key configuration status"
    )
