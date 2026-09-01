"""Tests for generate_full_proposal.py — D2 mapping.

D2: 5 sections of .rddf/improvements/<name>.md → canonical openspec proposal.md.
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
    generate_spec_delta,
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

- **In Scope**:
  - approve 升级
  - 完整 proposal.md 生成
  - iteration.json 状态流转
- **Out Scope**:
  - 不改变 archive 逻辑
  - 不修改 ADR-0003 职责边界

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
    # Adjusted from 500 to 450 after fix-generator-scope-extraction:
    # Capabilities/Impact split eliminates duplication, reducing output length.
    assert len(out) >= 450, f"Expected >=450 chars, got {len(out)}"


def test_generate_full_proposal_includes_acceptance_checkboxes():
    out = generate_full_proposal("my-change", SAMPLE)
    assert "- [ ]" in out, "Acceptance checkboxes must be preserved"


def test_generate_full_proposal_handles_missing_sections():
    """Sections missing from .rddf/improvements should produce empty mapped output, not crash."""
    minimal = "# x\n\n**阶段**: design\n**分类**: workflow\n**类型**: feature\n"
    out = generate_full_proposal("x", minimal)
    assert "## Why" in out
    assert "## What Changes" in out
    assert "## Capabilities" in out


def test_generate_full_proposal_change_name_in_title():
    out = generate_full_proposal("my-feature", SAMPLE)
    assert out.startswith("# my-feature\n")


# ---------------------------------------------------------------------------
# Content-correctness regression (2026-08-04): the Out of Scope / Capabilities
# / Impact blocks were previously HARDCODED to move-proposal-creation-to-design
# content, leaking irrelevant text into every generated proposal.md. These
# tests lock the fix: all three blocks must be derived from the .rddf/improvements
# input, never from a fixed template.
# ---------------------------------------------------------------------------


def test_no_hardcoded_legacy_proposal_content_leaks():
    """Out of Scope / Capabilities / Impact must not contain the hardcoded
    move-proposal-creation-to-design strings (the historical bug)."""
    out = generate_full_proposal("my-change", SAMPLE)
    leaked = [
        "design 阶段不生成 tasks.md",
        "design-proposal-creation",
        "design-content-review",
        "ADR-0025",
        "SKIP_DESIGN_HANDOFF=yes 存量路径行为不变",
    ]
    for text in leaked:
        assert text not in out, f"hardcoded legacy content leaked: {text!r}"


def test_out_of_scope_derived_from_improvements_input():
    """Out of Scope items must come from the .rddf/improvements 范围/Out Scope block."""
    out = generate_full_proposal("my-change", SAMPLE)
    assert "不改变 archive 逻辑" in out
    assert "不修改 ADR-0003 职责边界" in out
    # In Scope items must not be repeated under Out of Scope
    out_scope_section = out.split("**Out of Scope**:", 1)[1].split("## Capabilities", 1)[0]
    assert "approve 升级" not in out_scope_section


def test_capabilities_impact_derived_from_constraints():
    """Capabilities / Impact must reflect the .rddf/improvements 技术约束 items,
    not a fixed template."""
    out = generate_full_proposal("my-change", SAMPLE)
    assert "env-var 传参 (Oracle C1)" in out
    assert "jsonschema 严格校验" in out


def test_scope_split_handles_bullet_style_headers():
    """- **In Scope**: (dash-prefixed) sub-headers must be treated as section
    markers, not as scope items themselves."""
    md = SAMPLE.replace("**In Scope**:", "- **In Scope**:").replace(
        "**Out Scope**:", "- **Out Scope**:"
    )
    out = generate_full_proposal("my-change", md)
    # The marker line itself must not appear as a bullet item
    assert "\n- **In Scope**:" not in out
    assert "\n- **Out Scope**:" not in out
    assert "不改变 archive 逻辑" in out


def test_generate_spec_delta_acceptance_to_requirements():
    """验证 ## 验收标准 段的 - [ ] checkbox 映射到 ### Requirement + #### Scenario"""
    source = """# Test Proposal

## Capabilities

## Impact

## Acceptance

- [ ] 用户能批准 proposal
- [ ] 自动写入 specs/ 目录
"""
    result = generate_spec_delta(source, sub="test")
    assert "## ADDED Requirements" in result
    assert "### Requirement: acceptance-1" in result
    assert "### Requirement: acceptance-2" in result
    assert "#### Scenario:" in result
    assert "acceptance-1" in result


def test_generate_spec_delta_capabilities_to_requirements():
    """验证 ## Capabilities 段 MUST/MUST NOT 映射到 ### Requirement"""
    source = """## Capabilities

- **MUST**: 自动生成 spec.md
- **MUST NOT**: 覆盖已有 specs/
"""
    result = generate_spec_delta(source, sub="test")
    assert "### Requirement: capability-1" in result
    assert "### Requirement: capability-2" in result
    assert "MUST" in result
    assert "MUST NOT" in result


def test_generate_spec_delta_scenarios_inline():
    """验证 ## 关键场景 段 GIVEN/WHEN/THEN 嵌入对应 Requirement"""
    source = """## Acceptance

- [ ] 系统响应

## 关键场景

- **GIVEN** 用户已登录
- **WHEN** 触发操作
- **THEN** 系统响应
"""
    result = generate_spec_delta(source, sub="test")
    assert "#### Scenario:" in result
    assert "系统响应" in result


def test_generate_spec_delta_idempotent_input():
    """验证空 source_md 返回有效骨架(只有 ADDED Requirements 头)"""
    result = generate_spec_delta("", sub="empty")
    assert "## ADDED Requirements" in result
    # 无任何 requirement 也返回头
    assert "### Requirement" not in result


def test_generate_spec_delta_passes_openspec_v1_4_format():
    """验证输出包含 openspec v1.4 必填 delta 头"""
    source = "## Acceptance\n\n- [ ] 行为 A"
    result = generate_spec_delta(source, sub="v1")
    assert "## ADDED Requirements" in result
    assert "### Requirement:" in result
    assert "#### Scenario:" in result
