"""Tests for the tool registry."""

from workflows.tool_registry import (
    ToolRegistryEntry,
    build_tool_registry,
    build_selected_guides,
    get_planner_descriptions,
)


def test_user_registry_contains_tools(sample_registry):
    expected_tools = [
        "recall_memories", "store_memory", "forget_memory",
        "web_search", "web_extract",
        "search_documents", "search_knowledge_graph",
        "delegate_mission_task", "delegate_note_task",
        "delegate_flashcard_task", "delegate_automation_task", "delegate_audio_task",
    ]
    for name in expected_tools:
        assert name in sample_registry


def test_user_registry_excludes_admin_tools(sample_registry):
    assert "delegate_sql_task" not in sample_registry
    assert "delegate_os_task" not in sample_registry


def test_admin_registry_includes_admin_tools(sample_admin_registry):
    assert "delegate_sql_task" in sample_admin_registry
    assert "delegate_os_task" in sample_admin_registry
    assert sample_admin_registry["delegate_sql_task"].admin_only is True


def test_admin_registry_has_more_entries(sample_registry, sample_admin_registry):
    assert len(sample_admin_registry) == len(sample_registry) + 2


def test_registry_entries_have_content(sample_registry):
    for name, entry in sample_registry.items():
        assert isinstance(entry, ToolRegistryEntry)
        assert entry.name, f"{name} has empty name"
        assert entry.description, f"{name} has empty description"
        assert entry.guide, f"{name} has empty guide"


def test_get_planner_descriptions(sample_registry):
    text = get_planner_descriptions(sample_registry)
    # Each entry starts with "N. **name**:" — count numbered entries
    import re
    numbered = re.findall(r"^\d+\. \*\*", text, re.MULTILINE)
    assert len(numbered) == len(sample_registry)
    assert text.strip().startswith("1.")


def test_build_selected_guides_returns_guide(sample_registry):
    text = build_selected_guides(["web_search"], sample_registry)
    assert "web_search" in text
    assert "OTHER AVAILABLE TOOLS" in text


def test_build_selected_guides_deduplication(sample_registry):
    text = build_selected_guides(["web_search", "web_search"], sample_registry)
    count = text.count("## Tool: web_search")
    assert count == 1
