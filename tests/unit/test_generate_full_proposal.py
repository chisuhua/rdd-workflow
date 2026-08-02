"""Tests for generate_full_proposal.py — D2 mapping.

D2: 5 sections of improvements/<name>.md → canonical openspec proposal.md.
"""
import os
import sys
from pathlib import Path

import pytest

# Add project root to sys.path so the import works
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from skills.guide_design.scripts.generate_full_proposal import (  # noqa: E402
    generate_full_proposal,
    validate_improvements_head,
)


SAMPLE = """# my-change

**优先级**: P1 | **来源**: test
**阶段**: design | **分类**: workflow
**类型**: feature
**依赖**: | **特性**:

## 架构依据

ADR-0003 + ADR-0017 决定 design/plan 职责再分配。ADR-0016 锁定 handoff 契约。

## 范围

- approve 升级
- 完整 proposal.md 生成
- iteration.json 状态流转

## 关键场景

- 单条批准：AI 生成完整 proposal,用户确认后落盘
- 已有 proposal 改进:approve → flow → ...

## 技术约束

- env-var 传参 (Oracle C1)
- jsonschema 严格校验

## 验收标准

- [ ] proposal.md >= 500 字符
- [ ] 含 ADR-NNNN 引用
- [ ] In/Out Scope 完整
"""


def test_validate_head_parses_required_fields():
    head = validate_improvements_head(SAMPLE)
    assert head["阶段"] == "design"
    assert head["分类"] == "workflow"
    assert head["类型"] == "feature"


def test_validate_head_falls_back_when_missing():
    head = validate_improvements_head("# no head\n\n## 范围\n- a\n")
    assert head["阶段"] == "default"
    assert head["分类"] == "general"
    assert head["类型"] == "feature"  # default type


def test_generate_full_proposal_emits_canonical_sections():
    out = generate_full_proposal("my-change", SAMPLE)
    assert "## Why" in out
    assert "## What Changes" in out
    assert "In Scope" in out
    assert "Out of Scope" in out
    assert "## Capabilities" in out
    assert "## Impact" in out
    assert "## Acceptance" in out


def test_generate_full_proposal_preserves_adr_references():
    out = generate_full_proposal("my-change", SAMPLE)
    assert "ADR-0003" in out
    assert "ADR-0017" in out
    assert "ADR-0016" in out


def test_generate_full_proposal_meets_minimum_length():
    out = generate_full_proposal("my-change", SAMPLE)
    assert len(out) >= 500, f"Expected >=500 chars, got {len(out)}"


def test_generate_full_proposal_includes_acceptance_checkboxes():
    out = generate_full_proposal("my-change", SAMPLE)
    assert "- [ ]" in out, "Acceptance checkboxes must be preserved"


def test_generate_full_proposal_handles_missing_sections():
    """Sections missing from improvements should produce empty mapped output, not crash."""
    minimal = "# x\n\n**阶段**: design\n**分类**: workflow\n**类型**: feature\n"
    out = generate_full_proposal("x", minimal)
    assert "## Why" in out
    assert "## What Changes" in out
    assert "## Capabilities" in out


def test_generate_full_proposal_change_name_in_title():
    out = generate_full_proposal("my-feature", SAMPLE)
    assert out.startswith("# my-feature\n")
