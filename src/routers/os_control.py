"""OS Control endpoints — shell execution, browser automation, GUI control.

Provides:
    POST /os/shell           - Execute a shell command
    POST /os/shell/classify  - Classify a command's risk tier (no execution)
    DELETE /os/shell/session  - Close a user's PTY session
    POST /os/browser         - Execute a browser action
    POST /os/gui             - Execute a GUI action
    POST /os/approve         - Approve a pending OS action
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from core.concurrency import concurrency_manager
from core.dependencies import get_current_user
from core.exceptions import AuthorizationError, ValidationError
from infrastructure.os_control.risk_tier import RiskTier, classify_shell_command_risk
from infrastructure.os_control.schemas import (
    ApprovalRequest,
    ApprovalResponse,
    BrowserAction,
    BrowserActionType,
    BrowserResult,
    GUIAction,
    GUIActionType,
    GUIResult,
    OSActionType,
    ShellResult,
)
from models.user import User
from utils.log import log_info, log_warning

router = APIRouter(prefix="/os", tags=["os-control"])



class ShellExecuteRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=4096, description="Shell command to execute")
    working_directory: Optional[str] = Field(None, description="Working directory override")
    timeout_seconds: int = Field(30, ge=1, le=300, description="Max execution time")


class ShellClassifyRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=4096)


class ShellClassifyResponse(BaseModel):
    command: str
    risk_tier: int
    risk_label: str
    requires_approval: bool


class BrowserExecuteRequest(BaseModel):
    action: BrowserActionType
    url: Optional[str] = None
    selector: Optional[str] = None
    text: Optional[str] = None
    timeout_seconds: int = Field(10, ge=1, le=60)


class GUIExecuteRequest(BaseModel):
    action: GUIActionType
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    image_path: Optional[str] = None
    confidence: float = Field(0.9, ge=0.5, le=1.0)



@router.post("/shell", response_model=ShellResult, status_code=status.HTTP_200_OK)
async def execute_shell(
    body: ShellExecuteRequest,
    user: User = Depends(get_current_user),
):
    """Execute a shell command in the user's persistent PTY session.

    Requires admin role. Commands are risk-classified automatically.
    Tier 4+ commands should be pre-approved via the approval flow.
    """
    if not getattr(user, "is_admin", False) and user.role != "admin":
        raise AuthorizationError("OS shell access requires admin role")

    def _run():
        from services.os_control_service import os_control_service

        log_info(f"[OS] Shell: user={user.username} cmd={body.command[:80]}")
        return os_control_service.execute_shell(
            command=body.command,
            user_id=str(user.id),
            working_directory=body.working_directory,
            timeout_seconds=body.timeout_seconds,
        )

    return await concurrency_manager.run_in_thread(_run)


@router.post("/shell/classify", response_model=ShellClassifyResponse)
async def classify_shell(
    body: ShellClassifyRequest,
    user: User = Depends(get_current_user),
):
    """Classify a shell command's risk tier without executing it.

    Useful for the frontend to show the appropriate approval dialog
    before the command is actually run.
    """
    from infrastructure.os_control.risk_tier import RISK_TIER_GATES

    tier = classify_shell_command_risk(body.command)
    gate = RISK_TIER_GATES[tier]

    return ShellClassifyResponse(
        command=body.command,
        risk_tier=tier.value,
        risk_label=gate.label,
        requires_approval=gate.requires_approval,
    )


@router.delete("/shell/session", status_code=status.HTTP_204_NO_CONTENT)
async def close_shell_session(
    user: User = Depends(get_current_user),
):
    """Close the user's PTY shell session."""
    from services.os_control_service import os_control_service
    os_control_service.close_shell_session(str(user.id))



@router.post("/browser", response_model=BrowserResult)
async def execute_browser(
    body: BrowserExecuteRequest,
    user: User = Depends(get_current_user),
):
    """Execute a browser automation action.

    Requires admin role. Read actions (extract_text, screenshot) are tier 3;
    interactive actions (click, type, evaluate) are tier 4.
    """
    if not getattr(user, "is_admin", False) and user.role != "admin":
        raise AuthorizationError("Browser control requires admin role")

    action = BrowserAction(
        action=body.action,
        url=body.url,
        selector=body.selector,
        text=body.text,
        timeout_seconds=body.timeout_seconds,
    )

    def _run():
        from services.os_control_service import os_control_service
        log_info(f"[OS] Browser: user={user.username} action={body.action}")
        return os_control_service.execute_browser(action)

    return await concurrency_manager.run_in_thread(_run)



@router.post("/gui", response_model=GUIResult)
async def execute_gui(
    body: GUIExecuteRequest,
    user: User = Depends(get_current_user),
):
    """Execute a GUI automation action.

    Requires admin role. All GUI actions are tier 4 (explicit approval).
    """
    if not getattr(user, "is_admin", False) and user.role != "admin":
        raise AuthorizationError("GUI control requires admin role")

    action = GUIAction(
        action=body.action,
        x=body.x,
        y=body.y,
        text=body.text,
        image_path=body.image_path,
        confidence=body.confidence,
    )

    def _run():
        from services.os_control_service import os_control_service
        log_info(f"[OS] GUI: user={user.username} action={body.action}")
        return os_control_service.execute_gui(action)

    return await concurrency_manager.run_in_thread(_run)
