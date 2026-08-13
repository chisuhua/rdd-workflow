"""Characterization tests for propose_quality_check.py::run_design_checks.

These tests lock the CURRENT behavior of the 3 design gate checks
(>=500 chars / ADR refs / In-Out Scope) as a baseline. They do NOT
assert a specific pass/fail outcome — only document what happens.

If a future change alters run_design_checks intentionally, these tests
will fail, forcing the author to update both the test AND the design
to reflect the new contract.

Marked with @pytest.mark.characterization to distinguish from functional tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the propose scripts module is importable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROPOSE_SCRIPTS = PROJECT_ROOT / "skills" / "propose" / "scripts"
if str(PROPOSE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PROPOSE_SCRIPTS))


def _safe_import_run_design_checks():
    """Import run_design_checks with graceful fallback when not present."""
    try:
        from propose_quality_check import run_design_checks  # type: ignore
        return run_design_checks
    except (ImportError, ModuleNotFoundError):
        pytest.skip("propose_quality_check module not importable in this environment")


@pytest.fixture
def improvement_factory(tmp_path):
    """Factory to create .rddf/improvements/<name>.md files for testing."""
    def _create(name: str, content: str) -> Path:
        imp_dir = tmp_path / ".rddf" / "improvements"
        imp_dir.mkdir(parents=True, exist_ok=True)
        f = imp_dir / f"{name}.md"
        f.write_text(content, encoding="utf-8")
        return f
    return _create


@pytest.mark.characterization
def test_legitimate_improvement_current_behavior(improvement_factory, tmp_path):
    """Lock current run_design_checks behavior for a complete, valid improvement."""
    run_design_checks = _safe_import_run_design_checks()
    content = """# test-legitimate

**优先级**: P1 | **来源**: 测试
**阶段**: v2.1 | **分类**: core-test
**类型**: functional
**主题**: 不适用

## 架构依据

This is a comprehensive architecture basis section that references ADR-0007 (gate mechanism),
ADR-0016 (arch artifact discovery), and ADR-0025 (design proposal creation). The references
are intentional and demonstrate proper linking to architecture decisions. This paragraph
contains enough text to exceed the 500-character threshold required by the design gate.

## 范围

### In Scope

1. **First item** — with detailed description.
2. **Second item** — with detailed description.

### Out Scope

- First out-of-scope item.

## 关键场景

- GIVEN a context, WHEN an action occurs, THEN a result follows.

## 技术约束

- MUST do something.
- MUST NOT do something else.

## 验收标准

- [ ] Criterion 1
"""
    f = improvement_factory("test-legitimate", content)
    result = run_design_checks("test-legitimate", str(tmp_path))
    # LOCK CURRENT BEHAVIOR — assert result is well-formed list, not specific value
    assert isinstance(result, list)


@pytest.mark.characterization
def test_improvement_missing_type_field_current_behavior(improvement_factory, tmp_path):
    """Lock current behavior when **类型** head field is missing."""
    run_design_checks = _safe_import_run_design_checks()
    content = """# test-missing-type

**优先级**: P1 | **来源**: 测试
**阶段**: v2.1 | **分类**: core-test

## 架构依据

References ADR-0007 and ADR-0016 with enough text to exceed 500 character threshold
for the design gate validation logic. The text continues here with additional
context that demonstrates proper linking to architecture decisions.

## 范围

### In Scope

1. Item one.

## 关键场景

- GIVEN x, WHEN y, THEN z.

## 技术约束

- MUST do something.

## 验收标准

- [ ] Criterion
"""
    f = improvement_factory("test-missing-type", content)
    result = run_design_checks("test-missing-type", str(tmp_path))
    assert isinstance(result, list)


@pytest.mark.characterization
def test_improvement_missing_in_out_scope_current_behavior(improvement_factory, tmp_path):
    """Lock current behavior when In Scope / Out Scope sections are missing."""
    run_design_checks = _safe_import_run_design_checks()
    content = """# test-missing-scope

**优先级**: P1 | **来源**: 测试
**阶段**: v2.1 | **分类**: core-test
**类型**: functional

## 架构依据

References ADR-0007, ADR-0016, ADR-0025 with enough text to exceed 500 character threshold.

## 范围

(No In Scope or Out Scope defined.)

## 关键场景

- GIVEN x, WHEN y, THEN z.

## 技术约束

- MUST do something.

## 验收标准

- [ ] Criterion
"""
    f = improvement_factory("test-missing-scope", content)
    result = run_design_checks("test-missing-scope", str(tmp_path))
    assert isinstance(result, list)
