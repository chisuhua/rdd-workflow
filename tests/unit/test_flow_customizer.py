"""Tests for FlowCustomizer — flow.yaml customisation merger (ADR-0012).

FlowCustomizer.merge(template, flow_config, phase) merges a phase-template
dict with the per-phase customisations declared in a flow.yaml file.

The supported customisation shapes for this milestone are:

- ``{"insert_after": "<step_id>", "step": {...}}``   → splice step in
                                                        after the named step
- ``{"insert_before": "<step_id>", "step": {...}}``  → splice step in
                                                        before the named step
- ``{"replace": "<step_id>", "overrides": {...}}``   → merge overrides
                                                        into the named step
                                                        (preserves id)

The merger is non-mutating (it copies the steps list) and skips any phase
that has no customisations declared in flow_config.

These tests lock the public surface used by StepPipeline to materialise a
final step list for a phase before execution.
"""
from __future__ import annotations

import copy

import pytest

from skills._lib.flow_customizer import FlowCustomizer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_template():
    """A minimal phase template with two ordered steps: a, b."""
    return {
        "description": "Test phase",
        "steps": [
            {"id": "a", "skill": "default_a"},
            {"id": "b", "skill": "default_b"},
        ],
    }


# ---------------------------------------------------------------------------
# Tests — 6 cases
# ---------------------------------------------------------------------------

def test_no_customizations_identity(base_template):
    """Empty customisations leave the template steps unchanged."""
    flow_config: dict = {"customizations": {}}
    result = FlowCustomizer.merge(base_template, flow_config, phase="execute")
    assert [s["id"] for s in result["steps"]] == ["a", "b"]
    assert [s["skill"] for s in result["steps"]] == ["default_a", "default_b"]


def test_insert_after(base_template):
    """insert_after 'a' with step c → ['a', 'c', 'b']."""
    flow_config = {
        "customizations": {
            "execute": [
                {
                    "insert_after": "a",
                    "step": {"id": "c", "skill": "added_c"},
                }
            ]
        }
    }
    result = FlowCustomizer.merge(base_template, flow_config, phase="execute")
    assert [s["id"] for s in result["steps"]] == ["a", "c", "b"]


def test_insert_before(base_template):
    """insert_before 'b' with step c → ['a', 'c', 'b']."""
    flow_config = {
        "customizations": {
            "execute": [
                {
                    "insert_before": "b",
                    "step": {"id": "c", "skill": "added_c"},
                }
            ]
        }
    }
    result = FlowCustomizer.merge(base_template, flow_config, phase="execute")
    assert [s["id"] for s in result["steps"]] == ["a", "c", "b"]


def test_replace_skill(base_template):
    """replace 'a' with overrides skill='custom' → step a gets custom skill."""
    flow_config = {
        "customizations": {
            "execute": [
                {
                    "replace": "a",
                    "overrides": {"skill": "custom"},
                }
            ]
        }
    }
    result = FlowCustomizer.merge(base_template, flow_config, phase="execute")
    assert [s["id"] for s in result["steps"]] == ["a", "b"]
    assert result["steps"][0]["skill"] == "custom"
    # Untouched step keeps its original skill
    assert result["steps"][1]["skill"] == "default_b"
    # Original id preserved
    assert result["steps"][0]["id"] == "a"


def test_multiple_customizations(base_template):
    """insert_after + replace in the same phase: both applied, in order."""
    flow_config = {
        "customizations": {
            "execute": [
                {
                    "insert_after": "a",
                    "step": {"id": "c", "skill": "added_c"},
                },
                {
                    "replace": "b",
                    "overrides": {"skill": "custom_b"},
                },
            ]
        }
    }
    result = FlowCustomizer.merge(base_template, flow_config, phase="execute")
    assert [s["id"] for s in result["steps"]] == ["a", "c", "b"]
    assert result["steps"][1]["id"] == "c"
    assert result["steps"][2]["skill"] == "custom_b"


def test_unknown_phase_identity(base_template):
    """Customisations declared for 'plan' do not affect merging for 'ship'."""
    flow_config = {
        "customizations": {
            "plan": [
                {
                    "insert_after": "a",
                    "step": {"id": "c", "skill": "added_c"},
                }
            ]
        }
    }
    result = FlowCustomizer.merge(base_template, flow_config, phase="ship")
    assert [s["id"] for s in result["steps"]] == ["a", "b"]