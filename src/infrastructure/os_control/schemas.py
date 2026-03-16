"""Pydantic schemas for OS Control Layer.

Defines the input/output models for all OS control operations:
- Shell commands (PTY)
- Browser actions (Playwright)
- GUI actions (pyautogui)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from infrastructure.os_control.risk_tier import RiskTier


# =============================================================================
# Common
# =============================================================================

class OSActionType(str, Enum):
    """Top-level OS action categories."""
    SHELL = "shell"
    BROWSER = "browser"
    GUI = "gui"
    SCREEN_CAPTURE = "screen_capture"


class OSAction(BaseModel):
    """Base model for all OS control actions."""
    action_type: OSActionType
    risk_tier: RiskTier = Field(..., description="Declared risk tier for this action")
    description: str = Field("", description="Human-readable description of the action")
    user_id: Optional[str] = Field(None, description="User who initiated the action")
    session_id: Optional[str] = Field(None, description="PTY session identifier")


# =============================================================================
# Shell / PTY
# =============================================================================

class ShellCommand(BaseModel):
    """Input model for shell command execution."""
    command: str = Field(..., min_length=1, max_length=4096, description="Shell command to execute")
    working_directory: Optional[str] = Field(None, description="Working directory for the command")
    timeout_seconds: int = Field(30, ge=1, le=300, description="Maximum execution time")
    risk_tier: RiskTier = Field(
        default=RiskTier.EXPLICIT,
        description="Risk tier — auto-classified if not provided",
    )
    environment: Optional[Dict[str, str]] = Field(
        None,
        description="Additional environment variables for the command",
    )


class ShellResult(BaseModel):
    """Output model for shell command execution."""
    command: str = Field(..., description="The command that was executed")
    exit_code: int = Field(..., description="Process exit code (0 = success)")
    stdout: str = Field("", description="Standard output")
    stderr: str = Field("", description="Standard error output")
    execution_time_ms: int = Field(0, description="Execution time in milliseconds")
    timed_out: bool = Field(False, description="Whether the command timed out")
    working_directory: str = Field("", description="Working directory after execution")
    risk_tier: RiskTier = Field(..., description="Risk tier of the executed command")

    @property
    def success(self) -> bool:
        """Check if the command executed successfully."""
        return self.exit_code == 0 and not self.timed_out


# =============================================================================
# Browser (Playwright)
# =============================================================================

class BrowserActionType(str, Enum):
    """Browser control action types."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    EXTRACT_TEXT = "extract_text"
    SCREENSHOT = "screenshot"
    SCROLL = "scroll"
    WAIT = "wait"
    EVALUATE = "evaluate"


class BrowserAction(BaseModel):
    """Input model for browser control actions."""
    action: BrowserActionType = Field(..., description="Browser action to perform")
    url: Optional[str] = Field(None, description="URL for navigate action")
    selector: Optional[str] = Field(None, description="CSS selector for element interactions")
    text: Optional[str] = Field(None, description="Text to type or JavaScript to evaluate")
    timeout_seconds: int = Field(10, ge=1, le=60, description="Action timeout")
    risk_tier: RiskTier = Field(
        default=RiskTier.HARD_CONFIRM,
        description="Risk tier — tier 3 for reads, tier 4 for clicks/submits",
    )

    def model_post_init(self, __context: Any) -> None:
        """Auto-classify risk tier based on action type."""
        read_actions = {BrowserActionType.EXTRACT_TEXT, BrowserActionType.SCREENSHOT}
        if self.action in read_actions:
            self.risk_tier = RiskTier.HARD_CONFIRM
        elif self.action in {BrowserActionType.CLICK, BrowserActionType.TYPE_TEXT, BrowserActionType.EVALUATE}:
            self.risk_tier = RiskTier.EXPLICIT


class BrowserResult(BaseModel):
    """Output model for browser control results."""
    action: BrowserActionType
    success: bool = Field(..., description="Whether the action succeeded")
    content: Optional[str] = Field(None, description="Extracted text or screenshot path")
    url: Optional[str] = Field(None, description="Current page URL after action")
    title: Optional[str] = Field(None, description="Current page title")
    error: Optional[str] = Field(None, description="Error message if action failed")
    execution_time_ms: int = Field(0, description="Execution time in milliseconds")
    risk_tier: RiskTier = Field(..., description="Risk tier of the executed action")


# =============================================================================
# GUI (pyautogui)
# =============================================================================

class GUIActionType(str, Enum):
    """GUI control action types."""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE_TEXT = "type_text"
    HOTKEY = "hotkey"
    SCREENSHOT = "screenshot"
    FIND_ELEMENT = "find_element"
    MOVE_TO = "move_to"
    DRAG_TO = "drag_to"


class GUIAction(BaseModel):
    """Input model for GUI control actions."""
    action: GUIActionType = Field(..., description="GUI action to perform")
    x: Optional[int] = Field(None, description="Screen X coordinate")
    y: Optional[int] = Field(None, description="Screen Y coordinate")
    text: Optional[str] = Field(None, description="Text to type or hotkey combo")
    image_path: Optional[str] = Field(None, description="Image path for find_element")
    confidence: float = Field(0.9, ge=0.5, le=1.0, description="Image match confidence")
    risk_tier: RiskTier = Field(
        default=RiskTier.EXPLICIT,
        description="Risk tier — tier 4 for all GUI actions",
    )


class GUIResult(BaseModel):
    """Output model for GUI control results."""
    action: GUIActionType
    success: bool
    content: Optional[str] = Field(None, description="Screenshot path or found element info")
    position: Optional[Dict[str, int]] = Field(None, description="Element position {x, y}")
    error: Optional[str] = None
    execution_time_ms: int = 0
    risk_tier: RiskTier = Field(..., description="Risk tier of the executed action")


# =============================================================================
# Approval
# =============================================================================

class ApprovalRequest(BaseModel):
    """Model for requesting user approval for a risky action."""
    action_id: str = Field(..., description="Unique identifier for this action")
    action_type: OSActionType
    risk_tier: RiskTier
    description: str = Field(..., description="Human-readable description of the action")
    command_preview: str = Field("", description="Preview of the command/action")
    requires_text_confirmation: bool = Field(False)
    confirmation_text: Optional[str] = Field(
        None,
        description="Text the user must type to confirm (tier 5 only)",
    )
    timeout_seconds: int = Field(300)


class ApprovalResponse(BaseModel):
    """Model for user approval response."""
    action_id: str
    approved: bool
    confirmation_text: Optional[str] = Field(None, description="User-typed confirmation text")
    modified_command: Optional[str] = Field(
        None,
        description="User-modified command (if they edited before approving)",
    )
