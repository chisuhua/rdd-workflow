"""Tests for compute_theme_coverage algorithm.

Test groups:
1. Full coverage match (100%)
2. Partial coverage match (50%)
3. Legacy proposals without **主题** field (no false 0/N alarm)
4. ~skipped~ themes excluded from denominator
"""
import importlib.util
import sys
from pathlib import Path

WT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = WT_ROOT / "skills" / "guide-design" / "scripts" / "design_preflight.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("design_preflight_test", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_roadmap(tmp_path: Path, content: str) -> str:
    p = tmp_path / "roadmap.md"
    p.write_text(content, encoding="utf-8")
    return str(p)


def _write_proposal(tmp_path: Path, name: str, content: str) -> str:
    imp_dir = tmp_path / ".rddf" / "improvements"
    imp_dir.mkdir(parents=True, exist_ok=True)
    p = imp_dir / f"{name}.md"
    p.write_text(content, encoding="utf-8")
    return str(p)


# === Test Group 1: Full coverage match ===

def test_coverage_full_match(tmp_path):
    """All themes matched → 100% coverage."""
    mod = _load_module()
    _write_roadmap(tmp_path, """\
### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC；事件总线 |
""")
    _write_proposal(tmp_path, "p1", "**主题**: RBAC\n## 范围\n")
    _write_proposal(tmp_path, "p2", "**主题**: 事件总线\n## 范围\n")

    result = mod.compute_theme_coverage(
        project_root=str(tmp_path),
        roadmap_path=str(tmp_path / "roadmap.md"),
        improvements_dir=str(tmp_path / ".rddf" / "improvements"),
    )
    assert result["total_themes"] == 2
    assert result["covered"] == 2
    assert result["uncovered"] == []
    assert result["coverage_pct"] == 100.0
    assert result["unmapped_legacy_count"] == 0
    assert result["skipped_count"] == 0


# === Test Group 2: Partial coverage match ===

def test_coverage_partial_match(tmp_path):
    """1 of 2 themes matched → 50% coverage."""
    mod = _load_module()
    _write_roadmap(tmp_path, """\
### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC；事件总线 |
""")
    _write_proposal(tmp_path, "p1", "**主题**: RBAC\n## 范围\n")

    result = mod.compute_theme_coverage(
        project_root=str(tmp_path),
        roadmap_path=str(tmp_path / "roadmap.md"),
        improvements_dir=str(tmp_path / ".rddf" / "improvements"),
    )
    assert result["total_themes"] == 2
    assert result["covered"] == 1
    assert result["uncovered"] == ["事件总线"]
    assert result["coverage_pct"] == 50.0


# === Test Group 3: Legacy proposals without 主题 field ===

def test_coverage_legacy_no_subject_field(tmp_path):
    """Old proposals without **主题** field counted separately, no false alarm."""
    mod = _load_module()
    _write_roadmap(tmp_path, """\
### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC |
""")
    _write_proposal(tmp_path, "legacy", "**优先级**: P1\n## 范围\n")

    result = mod.compute_theme_coverage(
        project_root=str(tmp_path),
        roadmap_path=str(tmp_path / "roadmap.md"),
        improvements_dir=str(tmp_path / ".rddf" / "improvements"),
    )
    assert result["total_themes"] == 1
    assert result["covered"] == 0
    assert result["uncovered"] == ["RBAC"]
    assert result["unmapped_legacy_count"] == 1
    # coverage_pct = 0/1 = 0.0, but the display should use unmapped_legacy_count
    # to show "未标注主题: 1 个旧 proposal" separately, avoiding 0/N false alarm.
    assert result["coverage_pct"] == 0.0


# === Test Group 4: ~skipped~ themes excluded ===

def test_skipped_theme_excluded(tmp_path):
    """~skipped~ themes don't count toward denominator."""
    mod = _load_module()
    _write_roadmap(tmp_path, """\
### Phase 1: arch (phase-1)
#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | RBAC；事件总线 ~skipped~ |
""")

    result = mod.compute_theme_coverage(
        project_root=str(tmp_path),
        roadmap_path=str(tmp_path / "roadmap.md"),
        improvements_dir=str(tmp_path / ".rddf" / "improvements"),
    )
    assert result["total_themes"] == 1  # only RBAC, ~skipped~ excluded
    assert result["uncovered"] == ["RBAC"]
    assert result["skipped_count"] == 1


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))