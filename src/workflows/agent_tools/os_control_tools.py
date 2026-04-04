"""ReAct tools for OS control operations (admin-only).

Wraps os_control_service with risk-tier classification and HITL approval
for high-risk commands.
"""

from __future__ import annotations

import json
from typing import Optional

from langchain_core.tools import tool
from langgraph.types import interrupt

from infrastructure.os_control.risk_tier import RiskTier, classify_shell_command_risk
from utils.log import log_info, log_warning


def build_os_control_tools(user_id: str) -> list:
    """Build OS control tools (admin-only)."""

    @tool
    def execute_shell_command(
        command: str,
        working_directory: Optional[str] = None,
        timeout_seconds: int = 30,
    ) -> str:
        """Execute a shell command on the system.

        Commands are classified by risk tier. High-risk commands
        (delete, overwrite, system modification) require user approval.

        Prefer read-only commands for diagnostics. Avoid interactive commands.

        Args:
            command: The shell command to execute.
            working_directory: Optional working directory for execution.
            timeout_seconds: Maximum execution time (default 30s).

        Returns:
            JSON with command, exit_code, stdout, stderr, risk_tier, and timing.
        """
        from services.os_control_service import os_control_service

        risk = classify_shell_command_risk(command)

        if risk >= RiskTier.HARD_CONFIRM:
            response = interrupt({
                "type": "os_control_approval",
                "command": command,
                "risk_tier": risk.name,
                "risk_value": risk.value,
                "message": f"Command '{command}' classified as {risk.name} risk. Approve execution?",
            })

            action = response.get("action", "reject") if isinstance(response, dict) else "reject"
            if action == "reject":
                return json.dumps({
                    "status": "rejected",
                    "message": f"Command execution rejected (risk: {risk.name}).",
                })

        try:
            result = os_control_service.execute_shell(
                command=command,
                user_id=user_id,
                working_directory=working_directory,
                timeout_seconds=timeout_seconds,
            )
            return json.dumps({
                "command": command,
                "exit_code": result.exit_code,
                "stdout": result.stdout[:2000] if result.stdout else "",
                "stderr": result.stderr[:1000] if result.stderr else "",
                "success": result.exit_code == 0,
                "timed_out": result.timed_out,
                "risk_tier": risk.name,
                "execution_time_ms": result.execution_time_ms,
            }, default=str)
        except Exception as e:
            log_warning(f"[os_control] Shell command failed: {e}")
            return json.dumps({"error": str(e), "command": command})

    return [execute_shell_command]
