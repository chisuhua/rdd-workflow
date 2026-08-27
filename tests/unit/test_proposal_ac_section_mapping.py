"""Unit tests for _extract_section in generate_full_proposal.py — fix-proposal-ac-section-mapping.

Per fix-proposal-ac-section-mapping proposal acceptance:
  - _extract_section supports multiple candidate titles (list input)
  - First matching title wins (priority order)
  - Covers both ## 验收 and ## 验收标准 style variants
"""
import pytest

from skills.guide_design.scripts.generate_full_proposal import _extract_section


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def md_with_short_acceptance():
    """Improvements 文件用 ## 验收 (2 字) 标题 — 实际 rdd-workflow 用法."""
    return """# test-change

## 架构依据

Some why text.

## 范围

In scope bullet.

## 验收

- [ ] Item 1
- [ ] Item 2
- [ ] Item 3
"""


@pytest.fixture
def md_with_long_acceptance():
    """Improvements 文件用 ## 验收标准 (4 字) 标题 — 一些历史 proposal."""
    return """# test-change

## 架构依据

Some why text.

## 验收标准

- [ ] Item 1
- [ ] Item 2
"""


# ---------------------------------------------------------------------------
# Test: single title (backward compat)
# ---------------------------------------------------------------------------

def test_extract_section_single_title_still_works(md_with_short_acceptance):
    """Per AC: _extract_section single string input 仍然工作 (向后兼容)."""
    content = _extract_section(md_with_short_acceptance, "验收")
    assert "- [ ] Item 1" in content
    assert "- [ ] Item 3" in content
    assert "Some why text" not in content  # not bleeding into next section


# ---------------------------------------------------------------------------
# Test: list input with first-match-wins
# ---------------------------------------------------------------------------

def test_extract_section_list_input_matches_first_candidate(md_with_short_acceptance):
    """List input: ["验收", "验收标准"] 匹配 ## 验收 (first wins)."""
    content = _extract_section(md_with_short_acceptance, ["验收", "验收标准"])
    assert "- [ ] Item 1" in content
    assert "- [ ] Item 3" in content


def test_extract_section_list_input_falls_back_to_second(md_with_long_acceptance):
    """List input: ["验收", "验收标准"] fallback 到 ## 验收标准 if ## 验收 不存在."""
    content = _extract_section(md_with_long_acceptance, ["验收", "验收标准"])
    assert "- [ ] Item 1" in content
    assert "- [ ] Item 2" in content


# ---------------------------------------------------------------------------
# Test: missing section returns empty
# ---------------------------------------------------------------------------

def test_extract_section_returns_empty_when_missing(md_with_short_acceptance):
    """找不到任何候选项时返回空字符串."""
    content = _extract_section(md_with_short_acceptance, ["不存在的标题"])
    assert content == ""


def test_extract_section_list_returns_empty_when_all_missing(md_with_short_acceptance):
    """所有候选都缺失时返回空字符串."""
    content = _extract_section(
        md_with_short_acceptance, ["foo", "bar", "baz"]
    )
    assert content == ""


# ---------------------------------------------------------------------------
# Test: priority order (first match wins, not regex alternation)
# ---------------------------------------------------------------------------

def test_extract_section_first_match_wins_not_longest():
    """当文件同时含 ## 验收 和 ## 验收标准 时, list[0] 应优先."""
    md = """## 验收

first section content

## 验收标准

second section content
"""
    content = _extract_section(md, ["验收", "验收标准"])
    assert "first section content" in content
    assert "second section content" not in content


def test_extract_section_reverse_priority_gets_second():
    """list 反向 [验收标准, 验收] 时应返回 second section."""
    md = """## 验收

first section content

## 验收标准

second section content
"""
    content = _extract_section(md, ["验收标准", "验收"])
    assert "second section content" in content
    assert "first section content" not in content