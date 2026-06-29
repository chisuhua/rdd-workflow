"""Tests for TriggerEngine — flow.yaml trigger condition evaluator (ADR-0012).

TriggerEngine.evaluate(condition, context) resolves a string trigger
expression against a context dict. The supported condition grammar for
this milestone is intentionally minimal:

- "always"                                  → True
- "changes.any(<tag>)"                      → True iff any change in
                                              context["changes"] has
                                              <tag> in its tags list
- anything else (e.g. "unknown()")          → False
- "changes.any(<tag>)" with empty changes   → False (vacuous truth fails)

These tests lock the public surface consumed by the ship-side executor
when deciding whether a custom step should run.
"""
from __future__ import annotations

import pytest

from skills._lib.trigger_engine import TriggerEngine


# ---------------------------------------------------------------------------
# Tests — 5 cases
# ---------------------------------------------------------------------------

def test_always_trigger():
    """The literal condition 'always' resolves to True regardless of context."""
    assert TriggerEngine.evaluate("always", {}) is True
    assert TriggerEngine.evaluate("always", {"changes": []}) is True
    assert TriggerEngine.evaluate("always", {"changes": [{"tags": []}]}) is True


def test_changes_any_has_security():
    """changes.any('security') is True when at least one change has the security tag."""
    context = {
        "changes": [
            {"id": "add-login", "tags": ["auth", "security"]},
            {"id": "fix-typo", "tags": ["docs"]},
        ]
    }
    assert TriggerEngine.evaluate("changes.any(security)", context) is True


def test_changes_any_no_security():
    """changes.any('security') is False when no change has the security tag."""
    context = {
        "changes": [
            {"id": "fix-typo", "tags": ["docs"]},
            {"id": "rename", "tags": ["refactor"]},
        ]
    }
    assert TriggerEngine.evaluate("changes.any(security)", context) is False


def test_empty_changes():
    """changes.any(tag) on an empty changes list resolves to False (no evidence)."""
    context = {"changes": []}
    assert TriggerEngine.evaluate("changes.any(security)", context) is False
    # Also covers the case where 'changes' is missing entirely
    assert TriggerEngine.evaluate("changes.any(security)", {}) is False


def test_unknown_function():
    """Any condition expression that is not recognised resolves to False."""
    assert TriggerEngine.evaluate("unknown()", {"changes": []}) is False
    assert TriggerEngine.evaluate("garbage", {}) is False
    assert TriggerEngine.evaluate("", {}) is False