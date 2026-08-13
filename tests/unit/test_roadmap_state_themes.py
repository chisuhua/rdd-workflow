"""Unit tests for roadmap_state.get_phase_themes() — 5-column table parser.

Tests cover:
- 5-column single theme
- 5-column multiple themes (semicolon-separated)
- 5-column empty cell
- 4-column legacy backward compat
- Unknown phase returns empty list
- Special characters in themes (CJK, dots, parens)

Ref: openspec/changes/add-roadmap-proposal-guidance/specs/roadmap-proposal-guidance/spec.md
"""
import sys
import tempfile
from pathlib import Path

import pytest

from skills._lib import roadmap_state


def _write_roadmap(content: str) -> str:
    """Helper: write roadmap.md to temp file, return path."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
    tmp.write(content)
    tmp.close()
    return tmp.name


def test_get_phase_themes_5col_single_theme():
    """Single theme in 5-column table returns 1-element list."""
    roadmap = """\
# Roadmap

### Phase 1: 基础架构 (phase-1)
**目标**: test

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构设计 | 核心架构 | P0 | RBAC权限模型 |
"""
    path = _write_roadmap(roadmap)
    try:
        result = roadmap_state.get_phase_themes(path, "phase-1", "arch-design")
        assert result == ["RBAC权限模型"]
    finally:
        Path(path).unlink()


def test_get_phase_themes_5col_multiple_themes_semicolon():
    """Multiple themes separated by ; return list."""
    roadmap = """\
# Roadmap

### Phase 1: 基础架构 (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构设计 | 核心架构 | P0 | RBAC权限模型；事件总线契约；模块边界 |
"""
    path = _write_roadmap(roadmap)
    try:
        result = roadmap_state.get_phase_themes(path, "phase-1", "arch-design")
        assert result == ["RBAC权限模型", "事件总线契约", "模块边界"]
    finally:
        Path(path).unlink()


def test_get_phase_themes_5col_empty_cell():
    """Empty 5th column returns empty list (no constraint)."""
    roadmap = """\
# Roadmap

### Phase 1: 基础架构 (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构设计 | 核心架构 | P0 |  |
"""
    path = _write_roadmap(roadmap)
    try:
        result = roadmap_state.get_phase_themes(path, "phase-1", "arch-design")
        assert result == []
    finally:
        Path(path).unlink()


def test_get_phase_themes_4col_legacy_compat():
    """4-column legacy table returns empty list (backward compat)."""
    roadmap = """\
# Roadmap

### Phase 1: 基础架构 (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 |
|--------|------|------|--------|
| arch-design | 架构设计 | 核心架构 | P0 |
"""
    path = _write_roadmap(roadmap)
    try:
        result = roadmap_state.get_phase_themes(path, "phase-1", "arch-design")
        assert result == []
    finally:
        Path(path).unlink()


def test_get_phase_themes_unknown_phase_returns_empty():
    """Unknown phase_id returns empty list (not error)."""
    roadmap = """\
# Roadmap

### Phase 1: 基础架构 (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构设计 | 核心架构 | P0 | 主题A |
"""
    path = _write_roadmap(roadmap)
    try:
        result = roadmap_state.get_phase_themes(path, "phase-99", "arch-design")
        assert result == []
    finally:
        Path(path).unlink()


def test_get_phase_themes_special_chars_in_theme():
    """Themes with CJK, dots, parens, gt signs are preserved verbatim."""
    roadmap = """\
# Roadmap

### Phase 1: 基础架构 (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构设计 | 核心架构 | P0 | API v2.0 接口；测试覆盖率 > 80% |
"""
    path = _write_roadmap(roadmap)
    try:
        result = roadmap_state.get_phase_themes(path, "phase-1", "arch-design")
        assert result == ["API v2.0 接口", "测试覆盖率 > 80%"]
    finally:
        Path(path).unlink()


def test_get_phase_themes_skipped_theme_marker():
    """Themes with ~skipped~ marker are returned as-is (caller strips)."""
    roadmap = """\
# Roadmap

### Phase 1: 基础架构 (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构设计 | 核心架构 | P0 | RBAC；事件总线 ~skipped~ |
"""
    path = _write_roadmap(roadmap)
    try:
        result = roadmap_state.get_phase_themes(path, "phase-1", "arch-design")
        # ~skipped~ is part of the theme name; caller (compute_theme_coverage) strips
        assert result == ["RBAC", "事件总线 ~skipped~"]
    finally:
        Path(path).unlink()


def test_get_phase_themes_missing_roadmap_file():
    """Missing roadmap file returns empty list (no error)."""
    result = roadmap_state.get_phase_themes(
        "/nonexistent/path/roadmap.md", "phase-1", "arch-design"
    )
    assert result == []


def test_get_phase_themes_cross_phase_isolation():
    """Same theme name in different phases returns the right one."""
    roadmap = """\
# Roadmap

### Phase 1: 基础架构 (phase-1)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| arch-design | 架构 | 核心 | P0 | 事件总线 |

### Phase 2: 高级特性 (phase-2)

#### 任务分类
| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| core-impl | 实现 | 核心 | P0 | 事件总线 |
"""
    path = _write_roadmap(roadmap)
    try:
        result_p1 = roadmap_state.get_phase_themes(path, "phase-1", "arch-design")
        result_p2 = roadmap_state.get_phase_themes(path, "phase-2", "core-impl")
        assert result_p1 == ["事件总线"]
        assert result_p2 == ["事件总线"]
    finally:
        Path(path).unlink()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))