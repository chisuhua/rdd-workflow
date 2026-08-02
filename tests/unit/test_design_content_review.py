"""Tests for design_content_review.py — improvements-layer check (D4).

D4: design phase runs two-layer content review:
  1. improvements layer (this module): 5 sections, ADR refs, acceptance checkboxes,
     head fields (阶段 / 分类 / 类型).
  2. openspec proposal layer (uses run_design_checks from propose_quality_check).

This module returns a list of error strings (empty == pass). Severity
warning vs strict is decided upstream by STRICT_DESIGN_GATE=yes env var.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from skills.guide_design.scripts.design_content_review import review_improvements  # noqa: E402


GOOD = """# good

**优先级**: P1 | **来源**: test
**阶段**: design | **分类**: workflow
**类型**: feature
**依赖**: | **特性**:

## 架构依据

ADR-0003 reference.

## 范围

- item a

## 关键场景

- scenario b

## 技术约束

- constraint c

## 验收标准

- [ ] d
"""


def test_review_good_passes():
    errors = review_improvements(GOOD)
    assert errors == [], f"Expected no errors, got: {errors}"


def test_review_missing_head_flags_warning():
    bad = """# bad

## 架构依据

ADR-0003.

## 范围

- a

## 关键场景

- b

## 技术约束

- c

## 验收标准

- [ ] d
"""
    errors = review_improvements(bad)
    assert any("阶段" in e or "分类" in e for e in errors), \
        f"Expected missing head fields flagged, got: {errors}"


def test_review_missing_adr_flags_warning():
    text = GOOD.replace("ADR-0003", "no reference here")
    errors = review_improvements(text)
    assert any("ADR" in e for e in errors), \
        f"Expected ADR missing flagged, got: {errors}"


def test_review_acceptance_must_be_quantifiable():
    text = GOOD.replace("- [ ] d", "- d")
    errors = review_improvements(text)
    assert any("验收" in e or "checkbox" in e.lower() for e in errors), \
        f"Expected acceptance checkbox missing flagged, got: {errors}"


def test_review_missing_section_flags_warning():
    text = GOOD.replace("## 关键场景\n\n- scenario b\n\n", "")
    errors = review_improvements(text)
    assert any("关键场景" in e for e in errors)


def test_review_all_sections_missing_returns_all_errors():
    text = "# bare\n\n`code`\n"
    errors = review_improvements(text)
    # Should flag missing head fields, missing sections, missing ADR, missing checkboxes
    assert len(errors) >= 4, f"Expected >=4 errors, got: {errors}"


def test_review_empty_input_returns_errors():
    errors = review_improvements("")
    assert len(errors) > 0
