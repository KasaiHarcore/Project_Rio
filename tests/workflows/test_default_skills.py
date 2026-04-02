"""Tests for default prompt-only skills."""

from workflows.default_skills import DEFAULT_SKILLS, SKILL_NAMES


def test_default_skills_has_three_keys():
    assert set(DEFAULT_SKILLS.keys()) == {"gestures", "out_of_scope", "abusive"}


def test_skill_names_matches():
    assert SKILL_NAMES == frozenset({"gestures", "out_of_scope", "abusive"})


def test_skills_have_required_content():
    for name, skill in DEFAULT_SKILLS.items():
        assert skill["name"] == name
        assert skill["description"], f"{name} has empty description"
        assert skill["guide"], f"{name} has empty guide"
