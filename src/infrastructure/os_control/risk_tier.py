"""Risk Tier System for OS Control actions.

Defines the five-level risk tier system that gates OS-level operations.
Each action declares its risk_tier via Pydantic metadata — the gate fires
automatically without requiring LLM reasoning per call.

Tier table:
    | Tier | Examples                          | Gate             |
    |------|-----------------------------------|------------------|
    | 1    | web search, RAG read, notes read  | none             |
    | 2    | notes write, SQL SELECT           | soft confirm     |
    | 3    | SQL mutate, file write            | hard confirm     |
    | 4    | shell exec, browser click, GUI    | explicit approve |
    | 5    | destructive ops (rm, format)      | type to confirm  |
"""

from __future__ import annotations

from enum import IntEnum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class RiskTier(IntEnum):
    """Risk tier levels for OS control operations."""
    NONE = 1         # No gate — read-only, safe operations
    SOFT_CONFIRM = 2 # Soft confirmation — low-risk writes
    HARD_CONFIRM = 3 # Hard confirmation — data-mutating operations
    EXPLICIT = 4     # Explicit approval — shell, browser, GUI
    DESTRUCTIVE = 5  # Type-to-confirm — rm, format, overwrite


class GateRequirement(BaseModel):
    """Describes what approval gate a risk tier requires."""
    tier: RiskTier
    label: str = Field(..., description="Human-readable label for the gate")
    requires_approval: bool = Field(default=False)
    requires_explicit_text: bool = Field(
        default=False,
        description="If True, user must type the confirmation text to proceed",
    )
    auto_reject_timeout_seconds: int = Field(
        default=300,
        description="Seconds before an unanswered approval auto-rejects",
    )


# Pre-defined gate configurations for each tier
RISK_TIER_GATES: Dict[RiskTier, GateRequirement] = {
    RiskTier.NONE: GateRequirement(
        tier=RiskTier.NONE,
        label="No approval needed",
        requires_approval=False,
    ),
    RiskTier.SOFT_CONFIRM: GateRequirement(
        tier=RiskTier.SOFT_CONFIRM,
        label="Soft confirmation",
        requires_approval=True,
        auto_reject_timeout_seconds=600,
    ),
    RiskTier.HARD_CONFIRM: GateRequirement(
        tier=RiskTier.HARD_CONFIRM,
        label="Hard confirmation",
        requires_approval=True,
        auto_reject_timeout_seconds=300,
    ),
    RiskTier.EXPLICIT: GateRequirement(
        tier=RiskTier.EXPLICIT,
        label="Explicit approval required",
        requires_approval=True,
        auto_reject_timeout_seconds=120,
    ),
    RiskTier.DESTRUCTIVE: GateRequirement(
        tier=RiskTier.DESTRUCTIVE,
        label="Type to confirm — destructive operation",
        requires_approval=True,
        requires_explicit_text=True,
        auto_reject_timeout_seconds=60,
    ),
}


# Shell command patterns and their risk tiers
SHELL_COMMAND_RISK_PATTERNS: Dict[str, RiskTier] = {
    # Tier 5 — destructive
    "rm -rf": RiskTier.DESTRUCTIVE,
    "rm -r": RiskTier.DESTRUCTIVE,
    "format": RiskTier.DESTRUCTIVE,
    "mkfs": RiskTier.DESTRUCTIVE,
    "dd if=": RiskTier.DESTRUCTIVE,
    "> /dev/": RiskTier.DESTRUCTIVE,
    "shred": RiskTier.DESTRUCTIVE,
    "truncate": RiskTier.DESTRUCTIVE,

    # Tier 4 — explicit approval (default for shell)
    "sudo": RiskTier.EXPLICIT,
    "chmod": RiskTier.EXPLICIT,
    "chown": RiskTier.EXPLICIT,
    "kill": RiskTier.EXPLICIT,
    "pkill": RiskTier.EXPLICIT,
    "systemctl": RiskTier.EXPLICIT,
    "service": RiskTier.EXPLICIT,
    "iptables": RiskTier.EXPLICIT,
    "mount": RiskTier.EXPLICIT,
    "umount": RiskTier.EXPLICIT,
    "useradd": RiskTier.EXPLICIT,
    "userdel": RiskTier.EXPLICIT,
    "passwd": RiskTier.EXPLICIT,
    "pip install": RiskTier.EXPLICIT,
    "npm install": RiskTier.EXPLICIT,
    "apt": RiskTier.EXPLICIT,
    "yum": RiskTier.EXPLICIT,
    "brew": RiskTier.EXPLICIT,

    # Tier 3 — hard confirm (file writes)
    "mv": RiskTier.HARD_CONFIRM,
    "cp": RiskTier.HARD_CONFIRM,
    "mkdir": RiskTier.HARD_CONFIRM,
    "touch": RiskTier.HARD_CONFIRM,
    "tee": RiskTier.HARD_CONFIRM,
    "sed -i": RiskTier.HARD_CONFIRM,
    "git push": RiskTier.HARD_CONFIRM,
    "git commit": RiskTier.HARD_CONFIRM,
    "git checkout": RiskTier.HARD_CONFIRM,
    "git reset": RiskTier.HARD_CONFIRM,
    "docker": RiskTier.HARD_CONFIRM,
}


def classify_shell_command_risk(command: str) -> RiskTier:
    """Classify the risk tier of a shell command based on pattern matching.

    Scans the command string against known dangerous patterns and returns
    the highest matching risk tier. Defaults to EXPLICIT (tier 4) for
    unrecognized commands — shell execution is inherently risky.

    Args:
        command: The shell command string to classify.

    Returns:
        The RiskTier for the command.
    """
    command_lower = command.strip().lower()

    # Check from highest risk first
    highest_tier = RiskTier.EXPLICIT  # Default for shell commands

    for pattern, tier in sorted(
        SHELL_COMMAND_RISK_PATTERNS.items(),
        key=lambda x: x[1],
        reverse=True,
    ):
        if pattern in command_lower:
            return tier

    # Read-only commands can be lower tier
    read_only_prefixes = (
        "ls", "cat", "head", "tail", "less", "more", "grep", "find",
        "wc", "which", "where", "whoami", "pwd", "echo", "date", "uname",
        "df", "du", "free", "top", "ps", "env", "printenv", "hostname",
        "id", "groups", "file", "stat", "tree", "git status", "git log",
        "git diff", "git branch", "python --version", "node --version",
        "npm list", "pip list", "conda list", "type", "dir",
    )

    for prefix in read_only_prefixes:
        if command_lower.startswith(prefix):
            return RiskTier.HARD_CONFIRM  # Still tier 3 — shell access is sensitive

    return highest_tier
