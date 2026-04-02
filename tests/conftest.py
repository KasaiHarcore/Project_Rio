"""Shared fixtures for Project Rio tests."""

import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path so `from workflows.X import Y` works
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


@pytest.fixture
def sample_registry():
    """Build a tool/skill registry for a regular user."""
    from workflows.tool_registry import build_tool_registry

    return build_tool_registry("user")


@pytest.fixture
def sample_admin_registry():
    """Build a tool/skill registry for an admin user."""
    from workflows.tool_registry import build_tool_registry

    return build_tool_registry("admin")
