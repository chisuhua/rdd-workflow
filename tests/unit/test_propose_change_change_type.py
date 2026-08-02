"""Tests for create_skeleton_change change_type extraction."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from skills.propose.scripts.propose_change import create_skeleton_change  # noqa: E402


def _make_improvement(path: Path, type_value: str) -> None:
    """Write a minimal improvements/<name>.md with a 类型 head field."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# demo\n\n"
        f"**优先级**: P1 | **来源**: test\n"
        f"**阶段**: design | **分类**: workflow\n"
        f"**类型**: {type_value}\n"
        f"**依赖**: | **特性**:\n\n"
        f"## 架构依据\n\nADR-0003.\n\n"
        f"## 范围\n\n- a\n"
    )


def test_create_skeleton_writes_change_type(tmp_path):
    """create_skeleton_change should write change_type into roadmap-meta.yaml."""
    improvements_path = tmp_path / "improvements" / "demo.md"
    _make_improvement(improvements_path, "feature")

    openspec_dir = tmp_path / "openspec"
    openspec_dir.mkdir()

    result = create_skeleton_change(
        project_root=str(tmp_path),
        name="demo",
        current_phase="design",
        category="workflow",
        priority="P1",
    )
    assert result is True

    yaml_path = tmp_path / "openspec" / "changes" / "demo" / "roadmap-meta.yaml"
    assert yaml_path.exists()

    text = yaml_path.read_text()
    assert "change_type" in text, f"change_type missing from yaml:\n{text}"


def test_create_skeleton_defaults_change_type_when_missing(tmp_path):
    """When improvement has no **类型** field, change_type defaults to 'feature'."""
    improvements_path = tmp_path / "improvements" / "demo.md"
    improvements_path.parent.mkdir(parents=True, exist_ok=True)
    improvements_path.write_text(
        "# demo\n\n"
        "**优先级**: P1\n"
        "**阶段**: design | **分类**: workflow\n"
    )
    openspec_dir = tmp_path / "openspec"
    openspec_dir.mkdir()

    result = create_skeleton_change(
        project_root=str(tmp_path),
        name="demo",
        current_phase="design",
        category="workflow",
        priority="P1",
    )
    assert result is True

    yaml_path = tmp_path / "openspec" / "changes" / "demo" / "roadmap-meta.yaml"
    text = yaml_path.read_text()
    assert "change_type" in text
