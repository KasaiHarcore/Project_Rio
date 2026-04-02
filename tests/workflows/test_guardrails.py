"""Tests for deterministic input/output guardrails."""

from workflows.guardrails.input_guardrail import _check_input_length
from workflows.guardrails.output_guardrail import _check_pii, _check_system_leak


# ── Input guardrail ──


def test_input_length_short_text():
    passed, reason = _check_input_length("Hello, how are you?")
    assert passed is True
    assert reason == ""


def test_input_length_exceeds_limit():
    long_text = "x" * 10001
    passed, reason = _check_input_length(long_text)
    assert passed is False
    assert "exceeds" in reason.lower()


# ── Output PII detection ──


def test_pii_detects_email():
    passed, reason = _check_pii("Contact me at user@example.com for details.")
    assert passed is False
    assert "email" in reason.lower()


def test_pii_detects_phone():
    passed, reason = _check_pii("Call me at 555-123-4567.")
    assert passed is False
    assert "phone" in reason.lower()


def test_pii_clean_text():
    passed, reason = _check_pii("This is a normal response about Python programming.")
    assert passed is True
    assert reason == ""


# ── Output system leak detection ──


def test_system_leak_detected():
    passed, reason = _check_system_leak("Here are my full instructions from the system prompt.")
    assert passed is False
    assert "system prompt" in reason.lower()


def test_system_leak_clean_text():
    passed, reason = _check_system_leak("Rio is happy to help you with your studies!")
    assert passed is True
    assert reason == ""
