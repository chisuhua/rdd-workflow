"""Tests for fragment parser: duplicate-key detection + array syntax support.

Bug X1 fix: phase fragments had multiple `主题:` keys that the naive parser
silently last-wins'd, dropping 1-2 themes per phase. AUTO-INDEX therefore
showed only the last theme while the main doc Phase Skeleton table listed
all themes.

This test file exercises:
- AC-1: Duplicate keys raise ValueError (no silent drop)
- AC-2: Array syntax `主题: [a, b, c]` parses into Fragment.themes list
- AC-3 (covered in Task 2): Existing phase-N.md files migrated to array form
- AC-4 (covered in Task 1 + 2): Single-theme fragments continue to work
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure _lib is importable (project-local, per rdd-workflow layout)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from _lib.roadmap_state import Fragment, _parse_fragment_file  # noqa: E402


# ---------------------------------------------------------------------------
# AC-1: Duplicate keys must raise, not silently last-wins
# ---------------------------------------------------------------------------


def test_parse_fragment_detects_duplicate_keys(tmp_path):
    """Duplicate `主题:` keys must raise ValueError, not silently drop."""
    md = tmp_path / "phase-bad.md"
    md.write_text(
        "---\n"
        "id: phase-bad\n"
        "kind: phase\n"
        "status: active\n"
        "phase_refs: []\n"
        "主题: first theme\n"
        "主题: second theme\n"
        "主题: third theme\n"
        "---\n\nbody\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        _parse_fragment_file(md)


def test_parse_fragment_detects_any_duplicate_key(tmp_path):
    """Duplicate detection is general — not specific to `主题` key."""
    md = tmp_path / "phase-bad.md"
    md.write_text(
        "---\n"
        "id: phase-x\n"
        "kind: phase\n"
        "status: active\n"
        "status: done\n"  # duplicate status
        "---\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate.*status"):
        _parse_fragment_file(md)


# ---------------------------------------------------------------------------
# AC-2: Array syntax `主题: [a, b, c]` parses into themes list
# ---------------------------------------------------------------------------


def test_parse_fragment_array_theme_syntax(tmp_path):
    """`主题: [a, b, c]` parses into Fragment.themes as ordered list."""
    md = tmp_path / "phase-arr.md"
    md.write_text(
        "---\n"
        "id: phase-arr\n"
        "kind: phase\n"
        "status: active\n"
        "phase_refs: []\n"
        "主题: [完整多会话支持, 定时循环与事件触发, 提案生成阶段 — 自动跨仓分析]\n"
        "---\n\nbody\n",
        encoding="utf-8",
    )
    frag = _parse_fragment_file(md)
    assert frag is not None
    assert frag.themes == [
        "完整多会话支持",
        "定时循环与事件触发",
        "提案生成阶段 — 自动跨仓分析",
    ]


def test_fragment_themes_field_preserves_order(tmp_path):
    """themes list preserves input order; theme field also exposed (single-string compat)."""
    md = tmp_path / "phase-arr.md"
    md.write_text(
        "---\n"
        "id: phase-arr\n"
        "kind: phase\n"
        "status: active\n"
        "phase_refs: []\n"
        "主题: [first, second, third]\n"
        "---\n",
        encoding="utf-8",
    )
    frag = _parse_fragment_file(md)
    assert frag.themes == ["first", "second", "third"]
    # Backward compat: theme field returns first theme (or joined)
    assert frag.theme == "first" or frag.theme == "first, second, third"


# ---------------------------------------------------------------------------
# AC-4: Single-theme fragments continue to work (backward compat)
# ---------------------------------------------------------------------------


def test_parse_fragment_single_theme_backward_compat(tmp_path):
    """Single `主题: foo` line still parses correctly; themes=[foo]."""
    md = tmp_path / "phase-single.md"
    md.write_text(
        "---\n"
        "id: phase-single\n"
        "kind: phase\n"
        "status: active\n"
        "phase_refs: []\n"
        "主题: only one theme\n"
        "---\n",
        encoding="utf-8",
    )
    frag = _parse_fragment_file(md)
    assert frag is not None
    assert frag.themes == ["only one theme"]
    assert frag.theme == "only one theme"


def test_parse_fragment_no_theme_field(tmp_path):
    """Fragment without `主题` field has empty themes list."""
    md = tmp_path / "phase-notheme.md"
    md.write_text(
        "---\n"
        "id: phase-notheme\n"
        "kind: phase\n"
        "status: active\n"
        "phase_refs: []\n"
        "---\n",
        encoding="utf-8",
    )
    frag = _parse_fragment_file(md)
    assert frag is not None
    assert frag.themes == []
    assert frag.theme == ""


def test_parse_fragment_array_theme_handles_nested_parens(tmp_path):
    """Array syntax correctly handles commas inside nested parentheses.

    Regression: phase-4.md has `主题: [多方对称与回归, 多方对称 + 回归 (P1-P3, 后续)]`.
    Naive `v.split(',')` would split inside the parens, breaking the second theme.
    """
    md = tmp_path / "phase-nested.md"
    md.write_text(
        "---\n"
        "id: phase-nested\n"
        "kind: phase\n"
        "status: active\n"
        "phase_refs: []\n"
        "主题: [多方对称与回归, 多方对称 + 回归 (P1-P3, 后续)]\n"
        "---\n",
        encoding="utf-8",
    )
    frag = _parse_fragment_file(md)
    assert frag is not None
    assert frag.themes == [
        "多方对称与回归",
        "多方对称 + 回归 (P1-P3, 后续)",
    ], (
        f"nested parens comma confused parser; got {frag.themes!r}; "
        f"expected comma inside (...) to NOT split items"
    )


# ---------------------------------------------------------------------------
# AC-3: Real .rddf/roadmap/phases/ files all use array syntax after migration
# ---------------------------------------------------------------------------


def test_phase_fragments_use_array_theme():
    """All .rddf/roadmap/phases/phase-*.md files use 主题: [array] syntax (no duplicate keys)."""
    phases_dir = PROJECT_ROOT / ".rddf" / "roadmap" / "phases"
    assert phases_dir.is_dir(), f"phases dir missing: {phases_dir}"
    phase_files = sorted(phases_dir.glob("phase-*.md"))
    assert len(phase_files) > 0, "no phase files found"
    for phase_md in phase_files:
        content = phase_md.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        fm = parts[1]
        # Count occurrences of `主题:` (not `主题:` in body)
        theme_count = sum(1 for line in fm.splitlines() if line.strip().startswith("主题:"))
        assert theme_count <= 1, (
            f"{phase_md.name}: has {theme_count} duplicate 主题 keys "
            f"(expected 1 array line); needs migration to array syntax"
        )


# ---------------------------------------------------------------------------
# Fragment dataclass has 'themes' field (AC-2)
# ---------------------------------------------------------------------------


def test_fragment_dataclass_has_themes_field():
    """Fragment dataclass has `themes` field (list[str])."""
    import dataclasses
    field_names = {f.name for f in dataclasses.fields(Fragment)}
    assert "themes" in field_names, (
        f"Fragment dataclass missing `themes` field; "
        f"current fields: {sorted(field_names)}"
    )


# ---------------------------------------------------------------------------
# AC-7: update_objectives_sentinel writes the AGENTS.md AUTO: objectives block
# ---------------------------------------------------------------------------


def test_update_objectives_sentinel_writes_block(tmp_path):
    """Writes the AUTO: objectives block to AGENTS.md on first call."""
    obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
    obj_dir.mkdir(parents=True)
    (obj_dir / "objective-test.md").write_text(
        "---\n"
        "id: objective-test\n"
        "status: active\n"
        "priority: P1\n"
        "theme: test theme for sentinel\n"
        "created: 2026-09-28\n"
        "last_revised: 2026-09-28\n"
        "review_by: 2026-12-27\n"
        "owner: rdd-planner\n"
        "manual_deps: []\n"
        "---\n",
        encoding="utf-8",
    )
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# AGENTS\n\n<!-- before block content -->\n", encoding="utf-8")

    from _lib.roadmap_state import update_objectives_sentinel
    result = update_objectives_sentinel(str(tmp_path))
    assert result["inserted"] is True
    assert result["objective_count"] == 1

    content = agents.read_text(encoding="utf-8")
    assert "<!-- AUTO: objectives start -->" in content
    assert "<!-- AUTO: objectives end -->" in content
    assert "objective-test" in content
    assert "<!-- before block content -->" in content


def test_update_objectives_sentinel_replaces_existing_block(tmp_path):
    """Existing sentinels are replaced in-place; no duplicate sentinels."""
    obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
    obj_dir.mkdir(parents=True)
    (obj_dir / "obj-new.md").write_text(
        "---\n"
        "id: obj-new\n"
        "status: active\n"
        "priority: P1\n"
        "theme: new theme\n"
        "created: 2026-09-28\n"
        "last_revised: 2026-09-28\n"
        "review_by: 2026-12-27\n"
        "owner: rdd-planner\n"
        "manual_deps: []\n"
        "---\n",
        encoding="utf-8",
    )
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        "# AGENTS\n\n"
        "<!-- AUTO: objectives start -->\n"
        "OLD STALE CONTENT — should be replaced\n"
        "<!-- AUTO: objectives end -->\n"
        "\n<!-- footer -->\n",
        encoding="utf-8",
    )

    from _lib.roadmap_state import update_objectives_sentinel
    result = update_objectives_sentinel(str(tmp_path))
    assert result["inserted"] is False

    content = agents.read_text(encoding="utf-8")
    assert "OLD STALE CONTENT" not in content
    assert "obj-new" in content
    assert "<!-- footer -->" in content
    assert content.count("<!-- AUTO: objectives start -->") == 1
    assert content.count("<!-- AUTO: objectives end -->") == 1


def test_update_objectives_sentinel_handles_no_objectives_dir(tmp_path):
    """Missing objectives dir returns inserted=False; AGENTS.md unchanged."""
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# AGENTS\n", encoding="utf-8")

    from _lib.roadmap_state import update_objectives_sentinel
    result = update_objectives_sentinel(str(tmp_path))
    assert result["inserted"] is False
    assert result["objective_count"] == 0
    assert agents.read_text(encoding="utf-8") == "# AGENTS\n"


def test_update_objectives_sentinel_includes_active_deferred_completed(tmp_path):
    """Sentinel block includes active, deferred, AND completed statuses."""
    obj_dir = tmp_path / ".rddf" / "roadmap" / "objectives"
    obj_dir.mkdir(parents=True)
    for status in ("active", "deferred", "completed"):
        (obj_dir / f"obj-{status}.md").write_text(
            "---\n"
            f"id: obj-{status}\n"
            f"status: {status}\n"
            "priority: P1\n"
            "theme: t\n"
            "created: 2026-09-28\n"
            "last_revised: 2026-09-28\n"
            "review_by: 2026-12-27\n"
            "owner: rdd-planner\n"
            "manual_deps: []\n"
            "---\n",
            encoding="utf-8",
        )
    agents = tmp_path / "AGENTS.md"
    agents.write_text("# AGENTS\n", encoding="utf-8")

    from _lib.roadmap_state import update_objectives_sentinel
    result = update_objectives_sentinel(str(tmp_path))
    assert result["objective_count"] == 3
    content = agents.read_text(encoding="utf-8")
    for status in ("active", "deferred", "completed"):
        assert f"obj-{status}" in content
