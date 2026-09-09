"""Round-trip tests for generate_full_proposal.py.

5-段 improvement (.rddf/improvements/<name>.md) → full proposal.md
(openspec/changes/<name>/proposal.md) converter per ADR-0025 D1/D2.
"""
import sys
from pathlib import Path

import pytest

# Add to sys.path so we can import from skills/rdd-builder/scripts
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "rdd-builder" / "scripts"))

from generate_full_proposal import generate_full_proposal  # noqa: E402


SAMPLE_IMPROVEMENT = """# fix-sample

**优先级**: P1 | **来源**: 测试

## Why

The user wants to fix X.

## 范围

In Scope: A, B, C.

## Capabilities

- capability-sample

## Impact

Users benefit.

## Acceptance

- AC-1: foo works
- AC-2: bar works
- AC-3: baz works

## Reference

- ADR-0001
"""


def test_generate_full_proposal_populates_why():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Why" in out
    assert "The user wants to fix X" in out


def test_generate_full_proposal_populates_what_changes():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## What Changes" in out
    assert "- A" in out
    assert "- B" in out
    assert "- C" in out


def test_generate_full_proposal_populates_capabilities():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Capabilities" in out
    assert "- capability-sample" in out


def test_generate_full_proposal_populates_impact():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Impact" in out
    assert "Users benefit" in out


def test_generate_full_proposal_populates_acceptance():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "## Acceptance" in out
    assert "AC-1" in out
    assert "AC-2" in out
    assert "AC-3" in out


def test_generate_full_proposal_includes_change_name_in_title():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert out.startswith("# fix-sample")


def test_generate_full_proposal_no_placeholders():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "<skeleton motivation>" not in out
    assert "TBD" not in out
    assert "fill in details" not in out


def test_generate_full_proposal_handles_missing_acceptance():
    """If improvement lacks ## Acceptance, generate from ## Capabilities as fallback AC."""
    minimal = """# fix-min

## Why

Need to fix.

## 范围

Just one thing.

## Capabilities

- capability-x

## Impact

None.

## Reference
"""
    out = generate_full_proposal("fix-min", minimal)
    assert "## Acceptance" in out  # Fallback synthesized


def test_generate_full_proposal_handles_empty_improvement():
    """If improvement has only H1, generate a placeholder-but-valid proposal."""
    empty = "# fix-empty\n"
    out = generate_full_proposal("fix-empty", empty)
    assert out.startswith("# fix-empty")
    assert "## Why" in out
    assert "## What Changes" in out


def test_generate_full_proposal_preserves_references():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "ADR-0001" in out


def test_generate_full_proposal_preserves_priority_metadata():
    out = generate_full_proposal("fix-sample", SAMPLE_IMPROVEMENT)
    assert "P1" in out


def test_generate_full_proposal_generates_skeleton_for_invalid_input():
    """Passing non-string raises TypeError (defensive)."""
    with pytest.raises(TypeError):
        generate_full_proposal("fix-x", None)
