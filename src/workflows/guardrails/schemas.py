"""Pydantic models for structured LLM guardrail output."""

from pydantic import BaseModel, Field


class InputCheckResult(BaseModel):
    """Result of LLM-based input safety check."""

    is_safe: bool = Field(
        description="Whether the input is safe to process"
    )
    is_on_topic: bool = Field(
        description="Whether the input is related to studying, learning, or education"
    )
    is_prompt_injection: bool = Field(
        description="Whether the input attempts to override system instructions"
    )
    rejection_reason: str = Field(
        default="",
        description="Brief explanation if the input was rejected",
    )


class OutputCheckResult(BaseModel):
    """Result of LLM-based output safety check."""

    is_safe: bool = Field(
        description="Whether the output is safe to return to the user"
    )
    contains_system_leak: bool = Field(
        description="Whether the output leaks system prompt or internal instructions"
    )
    contains_harmful_content: bool = Field(
        description="Whether the output contains harmful, violent, or inappropriate content"
    )
    rejection_reason: str = Field(
        default="",
        description="Brief explanation if the output was rejected",
    )
