"""OS Control Layer — PTY shell, browser automation, GUI control, and risk-tiered execution.

This package provides Rio's operating system interaction surface:
- PTY shell sessions (persistent bash via subprocess/pexpect)
- Browser control via Playwright
- GUI control via pyautogui
- Risk-tier gating for all OS actions
"""

from infrastructure.os_control.risk_tier import RiskTier, RISK_TIER_GATES
from infrastructure.os_control.schemas import (
    OSAction,
    OSActionType,
    ShellCommand,
    ShellResult,
    BrowserAction,
    BrowserActionType,
    BrowserResult,
    GUIAction,
    GUIActionType,
    GUIResult,
)

__all__ = [
    "RiskTier",
    "RISK_TIER_GATES",
    "OSAction",
    "OSActionType",
    "ShellCommand",
    "ShellResult",
    "BrowserAction",
    "BrowserActionType",
    "BrowserResult",
    "GUIAction",
    "GUIActionType",
    "GUIResult",
]
