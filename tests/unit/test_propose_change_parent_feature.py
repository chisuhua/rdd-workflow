"""Tests for create_skeleton_change reading **特性** field as fallback parent_feature.

Background: `add-proposal-deps-and-features` defined `**特性**` as the design-time
feature tag, but create_skeleton_change only honored the explicit parent_feature
parameter — never read it from .rddf/improvements/<name>.md. These tests lock the missing
fallback.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from skills.propose.scripts.propose_change import create_skeleton_change  # noqa: E402


def _write_improvement(path: Path, feature_value: str) -> None:
    """Write a minimal .rddf/improvements/<name>.md with a **特性** head field."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# demo\n\n"
        "**优先级**: P1 | **来源**: test\n"
        "**阶段**: design | **分类**: workflow\n"
        "**类型**: feature\n"
        f"**依赖**: | **特性**: {feature_value}\n\n"
        "## 架构依据\n\nADR-0003.\n\n"
        "## 范围\n\n- a\n"
    )


def _setup_project(tmp_path: Path, feature_value: str) -> str:
    """Create a project with openspec/ + .rddf/improvements/ + an improvement file."""
    improvements_path = tmp_path / ".rddf/improvements" / "demo.md"
    _write_improvement(improvements_path, feature_value)
    (tmp_path / "openspec").mkdir(exist_ok=True)
    return str(tmp_path)


def test_create_skeleton_reads_特性_when_parent_feature_none(tmp_path):
    """When parent_feature=None and **特性** is set in .rddf/improvements, write it."""
    project_root = _setup_project(tmp_path, "wave-core")

    result = create_skeleton_change(
        project_root=project_root,
        name="demo",
        current_phase="design",
        category="workflow",
        priority="P1",
        parent_feature=None,
    )
    assert result is True

    yaml_path = Path(project_root) / "openspec" / "changes" / "demo" / "roadmap-meta.yaml"
    text = yaml_path.read_text()
    # parent_feature must be the quoted value from **特性**, not null
    assert 'parent_feature: "wave-core"' in text, (
        f"parent_feature should come from **特性** field, got:\n{text}"
    )


def test_create_skeleton_param_wins_over_特性_field(tmp_path):
    """Explicit parent_feature param overrides **特性** value (param wins)."""
    project_root = _setup_project(tmp_path, "wave-core")

    result = create_skeleton_change(
        project_root=project_root,
        name="demo",
        current_phase="design",
        category="workflow",
        priority="P1",
        parent_feature="param-wins",
    )
    assert result is True

    yaml_path = Path(project_root) / "openspec" / "changes" / "demo" / "roadmap-meta.yaml"
    text = yaml_path.read_text()
    assert 'parent_feature: "param-wins"' in text, (
        f"parent_feature param should win over **特性**, got:\n{text}"
    )


def test_create_skeleton_empty_特性_writes_null_parent_feature(tmp_path):
    """Empty **特性** value (or absent) writes null parent_feature (no crash)."""
    project_root = _setup_project(tmp_path, "")

    result = create_skeleton_change(
        project_root=project_root,
        name="demo",
        current_phase="design",
        category="workflow",
        priority="P1",
        parent_feature=None,
    )
    assert result is True

    yaml_path = Path(project_root) / "openspec" / "changes" / "demo" / "roadmap-meta.yaml"
    text = yaml_path.read_text()
    # Empty 特性 should fall through to null (matches pre-fix behavior for absent field)
    assert "parent_feature: null" in text, (
        f"empty **特性** should yield parent_feature: null, got:\n{text}"
    )


def test_create_skeleton_body_mention_does_not_pollute_head(tmp_path):
    """Body reference to **特性**: wave-core should NOT be picked up when head is empty."""
    improvements_path = tmp_path / ".rddf/improvements" / "demo.md"
    improvements_path.parent.mkdir(parents=True, exist_ok=True)
    improvements_path.write_text(
        "# demo\n\n"
        "**优先级**: P1 | **来源**: test\n"
        "**阶段**: design | **分类**: workflow\n"
        "**类型**: feature\n"
        "**依赖**: | **特性**:\n\n"
        "## 架构依据\n\n"
        "When .rddf/improvements contains `**特性**: wave-core` in body as example,\n"
        "the parser should NOT pick it up — only head **特性** matters.\n"
    )
    (tmp_path / "openspec").mkdir(exist_ok=True)

    result = create_skeleton_change(
        project_root=str(tmp_path),
        name="demo",
        current_phase="design",
        category="workflow",
        priority="P1",
        parent_feature=None,
    )
    assert result is True

    yaml_path = tmp_path / "openspec" / "changes" / "demo" / "roadmap-meta.yaml"
    text = yaml_path.read_text()
    # Empty head 特性 should not be polluted by body example
    assert "parent_feature: null" in text, (
        f"body mention of **特性** should not pollute empty head, got:\n{text}"
    )
    assert "wave-core" not in text, (
        f"body example value should NOT appear in parent_feature, got:\n{text}"
    )
