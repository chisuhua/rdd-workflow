"""Unit tests for design_preflight._read_roadmap_themes — fix-design-preflight-roadmap-format.

Per fix-design-preflight-roadmap-format proposal acceptance:
  - _read_roadmap_themes 支持 ## Phase Skeleton 表格格式
  - _read_roadmap_themes 保留对 ### Phase N: 段落格式的支持
  - compute_theme_coverage 在 Phase Skeleton 格式下返回 >0 themes
"""
import json
import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures: roadmap.md contents
# ---------------------------------------------------------------------------

NEW_FORMAT_ROADMAP = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 完整多会话支持 | active | | |
| phase-1 | 定时循环与事件触发 | active | | |
| phase-2 | 编排能力完善 | active | | |
| phase-2 | 阶段步骤化执行 | active | | |
| phase-3 | 流程定制层 | active | | |
"""

LEGACY_FORMAT_ROADMAP = """# Roadmap

### Phase 1: 早期 (phase-1)

| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| `core-arch` | 核心架构 | 主干 | high | 事件总线契约; 跨仓协议 |
| `infra-setup` | 基础设施 | 部署 | high | Docker镜像 |

### Phase 2: 中期 (phase-2)

| 分类ID | 名称 | 描述 | 优先级 | 预期改进方向 |
|--------|------|------|--------|--------------|
| `api-layer` | API 层 | 接口 | medium | REST 设计 |
"""

EMPTY_ROADMAP = """# Roadmap

No phase table here.
"""


@pytest.fixture
def new_format_path(tmp_path):
    p = tmp_path / "new_format_roadmap.md"
    p.write_text(NEW_FORMAT_ROADMAP, encoding="utf-8")
    return str(p)


@pytest.fixture
def legacy_format_path(tmp_path):
    p = tmp_path / "legacy_format_roadmap.md"
    p.write_text(LEGACY_FORMAT_ROADMAP, encoding="utf-8")
    return str(p)


@pytest.fixture
def empty_path(tmp_path):
    p = tmp_path / "empty_roadmap.md"
    p.write_text(EMPTY_ROADMAP, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Test: new format (Phase Skeleton)
# ---------------------------------------------------------------------------

def test_read_phase_skeleton_themes_extracts_all_themes(new_format_path):
    """Per AC #1: ## Phase Skeleton 格式返回所有 themes (本例 5 个)."""
    from skills.guide_design.scripts.design_preflight import _read_roadmap_themes
    themes = _read_roadmap_themes(new_format_path)
    assert len(themes) == 5
    theme_names = {t["theme"] for t in themes}
    assert "完整多会话支持" in theme_names
    assert "阶段步骤化执行" in theme_names


def test_read_phase_skeleton_themes_preserves_phase_id(new_format_path):
    """每个 theme 都关联到正确的 phase_id (phase-1, phase-2, ...)."""
    from skills.guide_design.scripts.design_preflight import _read_roadmap_themes
    themes = _read_roadmap_themes(new_format_path)
    phase_counts = {}
    for t in themes:
        phase_counts[t["phase"]] = phase_counts.get(t["phase"], 0) + 1
    assert phase_counts["phase-1"] == 2
    assert phase_counts["phase-2"] == 2
    assert phase_counts["phase-3"] == 1


# ---------------------------------------------------------------------------
# Test: legacy format (### Phase N: section + category table)
# ---------------------------------------------------------------------------

def test_read_legacy_roadmap_themes_still_supported(legacy_format_path):
    """Per AC #2: ### Phase N: 格式仍然解析正确."""
    from skills.guide_design.scripts.design_preflight import _read_roadmap_themes
    themes = _read_roadmap_themes(legacy_format_path)
    assert len(themes) == 4  # 事件总线契约; 跨仓协议; Docker镜像; REST 设计
    theme_names = {t["theme"] for t in themes}
    assert "事件总线契约" in theme_names
    assert "跨仓协议" in theme_names
    assert "Docker镜像" in theme_names
    assert "REST 设计" in theme_names


def test_read_legacy_roadmap_themes_preserves_category(legacy_format_path):
    """Legacy 格式的 category (分类ID) 被保留."""
    from skills.guide_design.scripts.design_preflight import _read_roadmap_themes
    themes = _read_roadmap_themes(legacy_format_path)
    categories = {t["category"] for t in themes}
    assert "`core-arch`" in categories
    assert "`infra-setup`" in categories
    assert "`api-layer`" in categories


# ---------------------------------------------------------------------------
# Test: empty roadmap
# ---------------------------------------------------------------------------

def test_read_empty_roadmap_returns_empty(empty_path):
    """空 roadmap 返回空列表 (不报错)."""
    from skills.guide_design.scripts.design_preflight import _read_roadmap_themes
    themes = _read_roadmap_themes(empty_path)
    assert themes == []


# ---------------------------------------------------------------------------
# Test: ~skipped~ themes excluded
# ---------------------------------------------------------------------------

def test_skipped_themes_are_excluded(tmp_path):
    """含 ~skipped~ 标记的 theme 不计入 coverage 分母."""
    skipped_roadmap = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 完整多会话支持 | active | | |
| phase-1 | 跳过项 ~skipped~ | active | | |
"""
    p = tmp_path / "skipped.md"
    p.write_text(skipped_roadmap, encoding="utf-8")

    from skills.guide_design.scripts.design_preflight import (
        _read_roadmap_themes, compute_theme_coverage,
    )
    themes = _read_roadmap_themes(str(p))
    assert len(themes) == 1
    assert themes[0]["theme"] == "完整多会话支持"


# ---------------------------------------------------------------------------
# Test: compute_theme_coverage end-to-end on current .rddf/roadmap.md
# ---------------------------------------------------------------------------

def test_compute_theme_coverage_returns_ten_themes_on_current_roadmap():
    """Per AC #4: 在当前 master .rddf/roadmap.md 上返回 10 themes 而不是 0."""
    repo_root = Path(__file__).resolve().parents[2]
    roadmap_path = repo_root / ".rddf" / "roadmap.md"
    improvements_dir = repo_root / ".rddf" / "improvements"

    if not roadmap_path.exists():
        pytest.skip(f"roadmap.md not found at {roadmap_path} (CI-only test)")

    from skills.guide_design.scripts.design_preflight import compute_theme_coverage
    result = compute_theme_coverage(
        str(repo_root), str(roadmap_path), str(improvements_dir),
    )
    assert result["total_themes"] == 10, (
        f"expected 10 themes, got {result['total_themes']}"
    )