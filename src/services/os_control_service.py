"""OS Control Service — orchestrates shell, browser, and GUI operations.

Central service that:
- Routes OS actions to the appropriate controller
- Enforces risk tier approval gates
- Logs all actions via the audit trail
- Manages PTY session lifecycle
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from infrastructure.os_control.browser_controller import BrowserController
from infrastructure.os_control.gui_controller import GUIController
from infrastructure.os_control.pty_session import PTYSession, pty_manager
from infrastructure.os_control.risk_tier import (
    RiskTier,
    RISK_TIER_GATES,
    classify_shell_command_risk,
)
from infrastructure.os_control.schemas import (
    ApprovalRequest,
    BrowserAction,
    BrowserResult,
    GUIAction,
    GUIResult,
    OSActionType,
    ShellCommand,
    ShellResult,
)
from utils.log import log_info, log_warning, log_error


class OSControlService:
    """Service layer for all OS control operations.

    Attributes:
        browser: Singleton browser controller instance.
        gui: Singleton GUI controller instance.
    """

    def __init__(self) -> None:
        self._browser: Optional[BrowserController] = None
        self._gui: Optional[GUIController] = None


    def execute_shell(
        self,
        command: str,
        user_id: str,
        *,
        working_directory: Optional[str] = None,
        timeout_seconds: int = 30,
        environment: Optional[Dict[str, str]] = None,
    ) -> ShellResult:
        """Execute a shell command in the user's PTY session.

        Args:
            command: Shell command to run.
            user_id: User identifier for session management.
            working_directory: Optional working directory override.
            timeout_seconds: Max execution time.
            environment: Additional environment variables.

        Returns:
            ShellResult with output and metadata.
        """
        session = pty_manager.get_or_create(
            session_id=user_id,
            working_directory=working_directory,
        )

        cmd = ShellCommand(
            command=command,
            working_directory=working_directory,
            timeout_seconds=timeout_seconds,
            environment=environment,
        )

        # Auto-classify risk tier
        cmd.risk_tier = classify_shell_command_risk(command)

        result = session.execute(cmd)

        log_info(
            f"[OSControl] Shell: user={user_id} cmd={command[:60]} "
            f"tier={result.risk_tier} exit={result.exit_code}"
        )

        return result

    def get_shell_risk_tier(self, command: str) -> RiskTier:
        """Pre-classify a command's risk tier without executing it.

        Useful for the frontend to show the appropriate approval UI
        before the command is actually run.
        """
        return classify_shell_command_risk(command)

    def close_shell_session(self, user_id: str) -> None:
        """Close a user's PTY session."""
        pty_manager.close_session(user_id)


    @property
    def browser(self) -> BrowserController:
        if self._browser is None:
            self._browser = BrowserController()
        return self._browser

    def execute_browser(self, action: BrowserAction) -> BrowserResult:
        """Execute a browser automation action.

        Args:
            action: BrowserAction to perform.

        Returns:
            BrowserResult with outcome.
        """
        result = self.browser.execute(action)

        log_info(
            f"[OSControl] Browser: action={action.action} "
            f"tier={result.risk_tier} success={result.success}"
        )

        return result


    @property
    def gui(self) -> GUIController:
        if self._gui is None:
            self._gui = GUIController()
        return self._gui

    def execute_gui(self, action: GUIAction) -> GUIResult:
        """Execute a GUI automation action.

        Args:
            action: GUIAction to perform.

        Returns:
            GUIResult with outcome.
        """
        result = self.gui.execute(action)

        log_info(
            f"[OSControl] GUI: action={action.action} "
            f"tier={result.risk_tier} success={result.success}"
        )

        return result


    def create_approval_request(
        self,
        action_type: OSActionType,
        risk_tier: RiskTier,
        description: str,
        command_preview: str = "",
    ) -> Optional[ApprovalRequest]:
        """Create an approval request if the risk tier requires it.

        Returns None if no approval is needed (tier 1).
        """
        gate = RISK_TIER_GATES[risk_tier]

        if not gate.requires_approval:
            return None

        return ApprovalRequest(
            action_id=uuid4().hex,
            action_type=action_type,
            risk_tier=risk_tier,
            description=description,
            command_preview=command_preview,
            requires_text_confirmation=gate.requires_explicit_text,
            confirmation_text=command_preview if gate.requires_explicit_text else None,
            timeout_seconds=gate.auto_reject_timeout_seconds,
        )


    def shutdown(self) -> None:
        """Clean up all resources."""
        pty_manager.close_all()
        if self._browser:
            self._browser.close()
        log_info("[OSControl] Service shut down")


# Module-level singleton
os_control_service = OSControlService()
