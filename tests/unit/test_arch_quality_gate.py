"""Tests for arch_quality_gate — qualitative arch-done checks beyond structural existence.

ADR-0018 introduces 4 warning-level checks that run on arch_done transition:
  - arch_alignment       — ADR cross-references in roadmap.md + theme docs resolve
  - adr_no_placeholders  — ADR files are not template stubs
  - arch_handoff_actionable — .arch-handoff.json carries actionable fields for guide-plan
  - file_size_limit      — _lib/*.py files do not exceed line cap

CHANGED 2026-09-30 (per ADR-0057):
  - Removed `arch_debt_recorded` check (gap-analysis artifact type deleted)
  - `arch_alignment` now scans theme docs (`docs/architecture/*.md`), not gap-analysis
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path

import pytest

from skills._lib.arch_quality_gate import (
    _check_arch_alignment,
    _check_adr_clarity,
    _check_handoff_actionable,
    _check_adr_shape,
    adr_shape_findings,
    _DEFAULT_ADR_LINE_LIMIT,
    strict_wrap,
    is_strict_mode,
    ArchQualityReport,
)


# ---------- fixtures ----------

@pytest.fixture
def project_with_clean_arch(tmp_path):
    """Project layout where all 4 checks pass cleanly."""
    # ADR with real content (not template stub)
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-three-phase.md").write_text(
        "# ADR-0001: 三阶段架构\n\n"
        "## 状态\n\n已采纳\n\n"
        "## 背景\n\nv1.x 单体架构难以演进。\n\n"
        "## 决策\n\n拆分为 arch → plan → ship 三阶段。\n\n"
        "## 影响\n\n下游消费方需读取 handoff。\n",
        encoding="utf-8",
    )
    (adr_dir / "ADR-0002-strict-mode.md").write_text(
        "# ADR-0002: 严格模式\n\n## 状态\n\n已采纳\n\n## 决策\n\nSTRICT_ARCH_GATE=yes 在 CI 中启用。\n",
        encoding="utf-8",
    )

    # Roadmap referencing real ADR IDs only
    roadmap = tmp_path / "roadmap.md"
    roadmap.write_text(
        "# 项目路线图\n\n"
        "**当前阶段**: phase-1\n\n"
        "## arch-design\n\n- ADR-0001 三阶段架构\n- ADR-0002 严格模式\n\n"
        "## infra-setup\n\n- (待规划)\n",
        encoding="utf-8",
    )

    # Theme doc referencing real ADRs (per ADR-0057; replaces gap-analysis)
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir()
    (arch_dir / "v2-migration.md").write_text(
        "# v2 Migration Theme\n\n"
        "## Primary ADRs\n\n"
        "- ADR-0001 三阶段架构\n"
        "- ADR-0002 严格模式\n\n"
        "## 当前状态\n\n"
        "迁移完成。\n",
        encoding="utf-8",
    )

    # Actionable handoff
    handoff_dir = tmp_path / ".rddf" / "state"
    handoff_dir.mkdir(parents=True)
    handoff = handoff_dir / ".arch-handoff.json"
    handoff.write_text(json.dumps({
        "arch_complete_at": "2026-07-10T10:00:00+08:00",
        "adr_count": 2,
        "completed_adr_ids": ["0001", "0002"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
        "version": 1,
    }), encoding="utf-8")

    return tmp_path


@pytest.fixture
def project_with_alignment_drift(tmp_path):
    """roadmap.md references ADR-NNNN that doesn't exist as file."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-real.md").write_text("# ADR-0001\n\n## 状态\n\n已采纳\n", encoding="utf-8")

    roadmap = tmp_path / "roadmap.md"
    roadmap.write_text(
        "**当前阶段**: phase-1\n\n## arch\n\n- ADR-0001\n- ADR-9999 (ghost reference)\n",
        encoding="utf-8",
    )

    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir()
    (arch_dir / "noop-gap-analysis.md").write_text(
        "# 差距分析\n\n## 3. 差距清单\n\n| # | x | 中 | P1 | done |\n",
        encoding="utf-8",
    )

    handoff_dir = tmp_path / ".rddf" / "state"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / ".arch-handoff.json").write_text(json.dumps({
        "arch_complete_at": "2026-07-10T10:00:00+08:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
        "version": 1,
    }), encoding="utf-8")

    return tmp_path


@pytest.fixture
def project_with_adr_placeholders(tmp_path):
    """ADR file is just a template copy with unfilled placeholders."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-stub.md").write_text(
        "# ADR-0001: <标题>\n\n"
        "> **编号**: NNNN\n\n"
        "## 状态\n\n待定\n\n"
        "## 背景\n\n<待补充>\n\n"
        "## 决策\n\n<TBD>\n",
        encoding="utf-8",
    )

    roadmap = tmp_path / "roadmap.md"
    roadmap.write_text("**当前阶段**: phase-1\n", encoding="utf-8")

    handoff_dir = tmp_path / ".rddf" / "state"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / ".arch-handoff.json").write_text(json.dumps({
        "arch_complete_at": "2026-07-10T10:00:00+08:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
        "version": 1,
    }), encoding="utf-8")

    return tmp_path


@pytest.fixture
def project_with_actionable_handoff_missing(tmp_path):
    """All artifacts present but handoff carries default current_phase + not discovered."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-real.md").write_text("# ADR-0001\n\n## 状态\n\n已采纳\n", encoding="utf-8")
    (tmp_path / "roadmap.md").write_text("# Roadmap\n\n**当前阶段**: default\n", encoding="utf-8")
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir()

    handoff_dir = tmp_path / ".rddf" / "state"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / ".arch-handoff.json").write_text(json.dumps({
        "arch_complete_at": "2026-07-10T10:00:00+08:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "default",  # not actionable
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": False, "created": True, "candidates_tried": 3},  # not found
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
        "version": 1,
    }), encoding="utf-8")

    return tmp_path


def _ctx(project_root):
    return {"project_root": str(project_root)}


# ---------- 1. alignment ----------

def test_arch_alignment_passes_when_all_refs_resolve(project_with_clean_arch):
    """When roadmap and gap-analysis reference only existing ADRs, alignment passes."""
    passed, severity = _check_arch_alignment(_ctx(project_with_clean_arch))
    assert passed is True
    assert severity is None


def test_arch_alignment_warns_on_ghost_adr_in_roadmap(project_with_alignment_drift):
    """roadmap.md references ADR-9999 which doesn't exist → warning."""
    passed, severity = _check_arch_alignment(_ctx(project_with_alignment_drift))
    assert passed is False
    assert severity == "warning"


def test_arch_alignment_warns_on_ghost_adr_in_theme_doc(tmp_path):
    """theme doc references a non-existent ADR → warning (per ADR-0057).

    Per ADR-0057, arch_alignment now scans all theme docs (*.md in
    architecture_dir) for ADR cross-references. Ghost ADR references in
    theme docs should warn (same as roadmap.md behavior).
    """
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-real.md").write_text("# ADR-0001\n\n## 状态\n\n已采纳\n", encoding="utf-8")
    (tmp_path / "roadmap.md").write_text("**当前阶段**: phase-1\n", encoding="utf-8")
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir()
    (arch_dir / "ghost-ref-theme.md").write_text(
        "# Theme\n\n## Primary ADRs\n\n- ADR-1234 (ghost)\n\n## 当前状态\n\nx\n",
        encoding="utf-8",
    )
    handoff_dir = tmp_path / ".rddf" / "state"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / ".arch-handoff.json").write_text(json.dumps({
        "arch_complete_at": "2026-07-10T10:00:00+08:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
        "version": 1,
    }), encoding="utf-8")

    passed, severity = _check_arch_alignment(_ctx(tmp_path))
    assert passed is False
    assert severity == "warning"


def test_arch_alignment_handles_missing_files_gracefully(tmp_path):
    """When roadmap.md or arch_dir missing → returns (True, None) to avoid noise."""
    # Bare layout: only ADRs, no roadmap, no gap-analysis
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001.md").write_text("# ADR-0001\n", encoding="utf-8")
    handoff_dir = tmp_path / ".rddf" / "state"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / ".arch-handoff.json").write_text(json.dumps({
        "arch_complete_at": "2026-07-10T10:00:00+08:00",
        "adr_count": 1,
        "completed_adr_ids": ["0001"],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
        "version": 1,
    }), encoding="utf-8")

    passed, severity = _check_arch_alignment(_ctx(tmp_path))
    assert passed is True
    assert severity is None


# ---------- 2. clarity ----------

def test_adr_clarity_passes_when_adrs_have_substance(project_with_clean_arch):
    """Real ADRs with non-trivial content → pass."""
    passed, severity = _check_adr_clarity(_ctx(project_with_clean_arch))
    assert passed is True
    assert severity is None


def test_adr_clarity_warns_on_template_placeholders(project_with_adr_placeholders):
    """ADR full of <待补充> / <TBD> / NNNN → warning."""
    passed, severity = _check_adr_clarity(_ctx(project_with_adr_placeholders))
    assert passed is False
    assert severity == "warning"


def test_adr_clarity_ignores_template_file(tmp_path):
    """ADR-0000-template.md should be excluded from clarity check."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0000-template.md").write_text(
        "# ADR-NNNN: <标题>\n\n> **编号**: NNNN\n\n## 状态\n\n<待补充>\n",
        encoding="utf-8",
    )
    (tmp_path / "roadmap.md").write_text("**当前阶段**: phase-1\n", encoding="utf-8")
    handoff_dir = tmp_path / ".rddf" / "state"
    handoff_dir.mkdir(parents=True)
    (handoff_dir / ".arch-handoff.json").write_text(json.dumps({
        "arch_complete_at": "2026-07-10T10:00:00+08:00",
        "adr_count": 0,
        "completed_adr_ids": [],
        "roadmap_exists": True,
        "current_phase": "phase-1",
        "plan_started_at": None,
        "adr_dir": "docs/adr",
        "roadmap_path": "roadmap.md",
        "architecture_dir": "docs/architecture",
        "adr_pattern": "ADR-*.md",
        "discovered": {
            "adr_dir": {"found": True, "created": False, "candidates_tried": 1},
            "roadmap_path": {"found": True, "created": False, "candidates_tried": 1},
            "architecture_dir": {"found": True, "created": False, "candidates_tried": 1},
        },
        "version": 1,
    }), encoding="utf-8")

    passed, severity = _check_adr_clarity(_ctx(tmp_path))
    assert passed is True
    assert severity is None


# ---------- 3. handoff actionable ----------

def test_handoff_actionable_passes_when_fields_complete(project_with_clean_arch):
    """Handoff with real adr_count, current_phase='phase-1', all discovered.found=true → pass."""
    passed, severity = _check_handoff_actionable(_ctx(project_with_clean_arch))
    assert passed is True
    assert severity is None


def test_handoff_actionable_warns_on_default_phase(project_with_actionable_handoff_missing):
    """current_phase='default' (not actionable) + discovered.adr_dir.found=false → warn."""
    passed, severity = _check_handoff_actionable(_ctx(project_with_actionable_handoff_missing))
    assert passed is False
    assert severity == "warning"


def test_handoff_actionable_warns_when_handoff_missing(tmp_path):
    """No .arch-handoff.json file → warn (re-emit guidance)."""
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "roadmap.md").write_text("**当前阶段**: phase-1\n", encoding="utf-8")
    # No .rddf/state dir
    passed, severity = _check_handoff_actionable(_ctx(tmp_path))
    assert passed is False
    assert severity == "warning"


# ---------- strict mode upgrade ----------

def test_is_strict_mode_default_false(monkeypatch):
    monkeypatch.delenv("STRICT_ARCH_GATE", raising=False)
    assert is_strict_mode() is False


def test_is_strict_mode_yes(monkeypatch):
    monkeypatch.setenv("STRICT_ARCH_GATE", "yes")
    assert is_strict_mode() is True


def test_is_strict_mode_true(monkeypatch):
    monkeypatch.setenv("STRICT_ARCH_GATE", "true")
    assert is_strict_mode() is True


def test_is_strict_mode_one(monkeypatch):
    monkeypatch.setenv("STRICT_ARCH_GATE", "1")
    assert is_strict_mode() is True


def test_is_strict_mode_empty_string(monkeypatch):
    monkeypatch.setenv("STRICT_ARCH_GATE", "")
    assert is_strict_mode() is False


def test_strict_wrap_upgrades_warning_to_error(monkeypatch):
    """When STRICT_ARCH_GATE=yes, strict_wrap converts (False, 'warning') → (False, 'error')."""
    monkeypatch.setenv("STRICT_ARCH_GATE", "yes")
    base = lambda ctx: (False, "warning")
    wrapped = strict_wrap(base)
    passed, severity = wrapped({})
    assert passed is False
    assert severity == "error"


def test_strict_wrap_keeps_warning_when_not_strict(monkeypatch):
    """Without STRICT_ARCH_GATE, warning stays warning."""
    monkeypatch.delenv("STRICT_ARCH_GATE", raising=False)
    base = lambda ctx: (False, "warning")
    wrapped = strict_wrap(base)
    passed, severity = wrapped({})
    assert passed is False
    assert severity == "warning"


def test_strict_wrap_passes_through_when_passing(monkeypatch):
    """Passing checks stay passing under strict mode (no false negatives)."""
    monkeypatch.setenv("STRICT_ARCH_GATE", "yes")
    base = lambda ctx: (True, None)
    wrapped = strict_wrap(base)
    passed, severity = wrapped({})
    assert passed is True
    assert severity is None


def test_strict_wrap_passes_through_errors(monkeypatch):
    """Errors are not modified by strict_wrap (already blocking)."""
    monkeypatch.setenv("STRICT_ARCH_GATE", "yes")
    base = lambda ctx: (False, "error")
    wrapped = strict_wrap(base)
    passed, severity = wrapped({})
    assert passed is False
    assert severity == "error"


# ---------- strict_wrap parameterization (ADR-0019) ----------


def test_strict_wrap_with_custom_env_var_reads_it(monkeypatch):
    """strict_wrap(env_var='STRICT_CHANGE_GATE') reads STRICT_CHANGE_GATE, not STRICT_ARCH_GATE."""
    monkeypatch.delenv("STRICT_ARCH_GATE", raising=False)
    monkeypatch.setenv("STRICT_CHANGE_GATE", "yes")
    base = lambda ctx: (False, "warning")
    wrapped = strict_wrap(base, env_var="STRICT_CHANGE_GATE")
    passed, severity = wrapped({})
    assert passed is False
    assert severity == "error"


def test_strict_wrap_with_custom_env_var_default_off(monkeypatch):
    """strict_wrap(env_var='STRICT_CHANGE_GATE') without STRICT_CHANGE_GATE keeps warning."""
    monkeypatch.delenv("STRICT_CHANGE_GATE", raising=False)
    monkeypatch.setenv("STRICT_ARCH_GATE", "yes")
    base = lambda ctx: (False, "warning")
    wrapped = strict_wrap(base, env_var="STRICT_CHANGE_GATE")
    passed, severity = wrapped({})
    assert passed is False
    assert severity == "warning"


def test_is_strict_mode_with_custom_env_var(monkeypatch):
    """is_strict_mode(env_var='STRICT_CHANGE_GATE') reads the specified env var."""
    monkeypatch.delenv("STRICT_ARCH_GATE", raising=False)
    monkeypatch.delenv("STRICT_CHANGE_GATE", raising=False)
    assert is_strict_mode(env_var="STRICT_CHANGE_GATE") is False
    monkeypatch.setenv("STRICT_CHANGE_GATE", "yes")
    assert is_strict_mode(env_var="STRICT_CHANGE_GATE") is True
    assert is_strict_mode() is False


def test_strict_wrap_default_env_var_backward_compat(monkeypatch):
    """strict_wrap() without env_var param defaults to STRICT_ARCH_GATE (ADR-0018 compat)."""
    monkeypatch.setenv("STRICT_ARCH_GATE", "yes")
    base = lambda ctx: (False, "warning")
    wrapped = strict_wrap(base)
    passed, severity = wrapped({})
    assert passed is False
    assert severity == "error"


def test_strict_wrap_both_env_vars_independent(monkeypatch):
    """STRICT_ARCH_GATE=yes alone does not affect a strict_wrap(env_var='STRICT_CHANGE_GATE')."""
    monkeypatch.setenv("STRICT_ARCH_GATE", "yes")
    monkeypatch.delenv("STRICT_CHANGE_GATE", raising=False)
    base = lambda ctx: (False, "warning")
    wrapped = strict_wrap(base, env_var="STRICT_CHANGE_GATE")
    passed, severity = wrapped({})
    assert passed is False
    assert severity == "warning"


# ---------- ArchQualityReport aggregator ----------

def test_arch_quality_report_aggregates_results(project_with_clean_arch):
    """ArchQualityReport.verify returns aggregate passed/warnings."""
    report = ArchQualityReport.verify(str(project_with_clean_arch))
    assert isinstance(report, ArchQualityReport)
    assert report.passed is True
    assert report.warnings == []


def test_arch_quality_report_collects_warnings(project_with_alignment_drift):
    """When alignment drifts, report surfaces it as warning name."""
    report = ArchQualityReport.verify(str(project_with_alignment_drift))
    assert "arch_alignment" in report.warnings


def test_arch_quality_report_strict_mode_promotes_to_errors(project_with_alignment_drift, monkeypatch):
    """Under STRICT_ARCH_GATE=yes, ArchQualityReport surfaces strict_mode=True for downstream consumers.

    `ArchQualityReport.verify()` itself does not promote warnings to failed
    checks — that responsibility belongs to the registration layer
    (`strict_wrap()` in `gate.py`). The report only carries the strict_mode
    flag so downstream consumers can decide.
    """
    monkeypatch.setenv("STRICT_ARCH_GATE", "yes")
    report = ArchQualityReport.verify(str(project_with_alignment_drift))
    assert report.strict_mode is True
    assert "arch_alignment" in report.warnings
    assert "arch_alignment" not in report.failed_checks

# ---------- 5. ADR shape (opt-in, added 2026-10-28) ----------

_WELL_FORMED_ADR = """# ADR-0007: 单模型双后端

> **状态**: 已采纳
> **日期**: 2026-10-28
> **决策者**: architect

## Context

双后端并行导致语义漂移。

## Decision

只保留一种模型，两个后端。

### 备选方案

| 备选 | 结论 | 理由 |
|---|---|---|
| A 保留双模 | 拒绝 | 模态开关带来二义 |
| B 单模双后端 | 接受 | 模型唯一 |
| C 双模双后端 | 拒绝 | 差分门禁无法定义 |

## Consequences

### 正面

后端差异可机器判定。

### 负面 / 风险

CI 需要 build 能力。

## Verification

- [ ] **V-1** 差分门禁首跑为空 ⇒ 通过

## References

- ADR-0001
"""


def _write_adr(tmp_path, name, body):
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    path = adr_dir / name
    path.write_text(body, encoding="utf-8")
    return path


def test_adr_shape_passes_on_well_formed_adr(tmp_path):
    _write_adr(tmp_path, "ADR-0007-shape.md", _WELL_FORMED_ADR)
    passed, severity = _check_adr_shape(_ctx(tmp_path))
    assert passed is True
    assert severity is None


def test_adr_shape_warns_on_oversized_adr(tmp_path):
    body = _WELL_FORMED_ADR + "\n".join(f"- 推导行 {i}" for i in range(320))
    _write_adr(tmp_path, "ADR-0008-big.md", body)
    passed, severity = _check_adr_shape(_ctx(tmp_path))
    assert passed is False
    assert severity == "warning"


def test_adr_shape_line_limit_env_override(tmp_path, monkeypatch):
    body = _WELL_FORMED_ADR + "\n".join(f"- 推导行 {i}" for i in range(40))
    _write_adr(tmp_path, "ADR-0009-mid.md", body)
    monkeypatch.setenv("ARCH_ADR_LINE_LIMIT", "10")
    passed, _ = _check_adr_shape(_ctx(tmp_path))
    assert passed is False
    monkeypatch.setenv("ARCH_ADR_LINE_LIMIT", "10000")
    passed, _ = _check_adr_shape(_ctx(tmp_path))
    assert passed is True


def test_adr_shape_warns_on_missing_section(tmp_path):
    body = "# ADR-0010: 缺章节\n\n## Context\n\n背景。\n\n## Decision\n\n决定。\n"
    _write_adr(tmp_path, "ADR-0010-missing.md", body)
    passed, severity = _check_adr_shape(_ctx(tmp_path))
    assert passed is False
    assert severity == "warning"


def test_adr_shape_warns_on_process_log_markers(tmp_path):
    body = _WELL_FORMED_ADR + "\n## 审稿记录\n\n第 2 轮 critic 提出 1 BLOCKER。\n"
    _write_adr(tmp_path, "ADR-0011-log.md", body)
    passed, severity = _check_adr_shape(_ctx(tmp_path))
    assert passed is False
    assert severity == "warning"


def test_adr_shape_warns_on_long_status_line(tmp_path):
    body = _WELL_FORMED_ADR.replace(
        "> **状态**: 已采纳",
        "> **状态**: 已采纳（v1.0 → v1.1 → v1.2 → v1.3 → v1.4）" + "（含逐版裁决摘要）" * 30,
    )
    _write_adr(tmp_path, "ADR-0012-status.md", body)
    passed, severity = _check_adr_shape(_ctx(tmp_path))
    assert passed is False
    assert severity == "warning"


def test_adr_shape_scopes_to_explicit_files(tmp_path):
    good = _write_adr(tmp_path, "ADR-0013-good.md", _WELL_FORMED_ADR)
    _write_adr(tmp_path, "ADR-0014-bad.md", "x\n")
    ctx = _ctx(tmp_path)
    ctx["adr_files"] = [str(good)]
    passed, _ = _check_adr_shape(ctx)
    assert passed is True


def test_adr_shape_not_registered_in_report_by_default(tmp_path, monkeypatch):
    """Existing ADRs are pre-existing debt — the shape check stays opt-in."""
    monkeypatch.delenv("ARCH_SHAPE_CHECK", raising=False)
    body = "# ADR-0015\n\n## Context\n\n背景\n"
    _write_adr(tmp_path, "ADR-0015-thin.md", body)
    report = ArchQualityReport.verify(str(tmp_path))
    assert "adr_shape" not in report.warnings
    assert "adr_shape" not in report.detail


def test_adr_shape_registered_in_report_when_opted_in(tmp_path, monkeypatch):
    monkeypatch.setenv("ARCH_SHAPE_CHECK", "yes")
    body = "# ADR-0016\n\n## Context\n\n背景\n"
    _write_adr(tmp_path, "ADR-0016-thin.md", body)
    report = ArchQualityReport.verify(str(tmp_path))
    assert "adr_shape" in report.warnings


# ---------- 6. ADR shape: same-source budget + new signals (added 2026-11-17) ----------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TEMPLATE = _REPO_ROOT / "docs" / "adr" / "ADR-0000-template.md"
_SHAPE_CLI = _REPO_ROOT / "skills" / "rdd-arch" / "scripts" / "adr_shape_check.sh"


def _findings(tmp_path, name, body):
    """Write one ADR and return its structured shape findings."""
    _write_adr(tmp_path, name, body)
    return adr_shape_findings({"project_root": str(tmp_path)})


def _signals(findings):
    return {f.signal for f in findings}


def test_adr_shape_line_limit_matches_template_budget():
    """同源断言：机械门预算必须等于 ADR 模板里的散文预算。

    Without this, the two budgets drift apart silently (they did: template said
    250, the machine default was 300).
    """
    text = _TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"≤\s*(\d+)\s*行", text)
    assert m, "ADR-0000-template.md no longer states a line budget"
    assert int(m.group(1)) == _DEFAULT_ADR_LINE_LIMIT


def test_adr_shape_missing_verification_section_is_reported(tmp_path):
    body = _WELL_FORMED_ADR.replace("## Verification\n\n- [ ] **V-1** 差分门禁首跑为空 ⇒ 通过\n\n", "")
    findings = _findings(tmp_path, "ADR-0020-noverif.md", body)
    assert "missing_verification" in _signals(findings)


def test_adr_shape_bilingual_verification_section_passes(tmp_path):
    """`## 验证`（h2）是合法的 Verification 章节 —— 双语仓库不能只认英文。"""
    body = _WELL_FORMED_ADR.replace(
        "## Verification\n\n- [ ] **V-1** 差分门禁首跑为空 ⇒ 通过\n",
        "## 验证\n\n- [ ] **V-1** 差分门禁首跑为空 ⇒ 通过\n",
    )
    findings = _findings(tmp_path, "ADR-0021-zh.md", body)
    assert "missing_verification" not in _signals(findings)


def test_adr_shape_h3_verification_prose_is_not_a_section(tmp_path):
    """`### 验证 ADR-0048 + ADR-0049 零 regression` 是散文子标题，不是验收章。

    它不能被当成 Verification 章节 —— 否则会「假阴性放行」一份没有验收章的 ADR。
    """
    body = _WELL_FORMED_ADR.replace(
        "## Verification\n\n- [ ] **V-1** 差分门禁首跑为空 ⇒ 通过\n",
        "### 验证 ADR-0048 + ADR-0049 零 regression\n\n实测通过。\n",
    )
    findings = _findings(tmp_path, "ADR-0022-h3.md", body)
    assert "missing_verification" in _signals(findings)


def test_adr_shape_verification_section_without_checkbox_is_reported(tmp_path):
    body = _WELL_FORMED_ADR.replace(
        "## Verification\n\n- [ ] **V-1** 差分门禁首跑为空 ⇒ 通过\n",
        "## Verification\n\n待补充。\n",
    )
    findings = _findings(tmp_path, "ADR-0023-empty.md", body)
    assert "verification_section_empty" in _signals(findings)


def test_adr_shape_alternatives_table_missing_is_reported(tmp_path):
    body = _WELL_FORMED_ADR.replace(
        "| 备选 | 结论 | 理由 |\n|---|---|---|\n| A 保留双模 | 拒绝 | 模态开关带来二义 |\n"
        "| B 单模双后端 | 接受 | 模型唯一 |\n| C 双模双后端 | 拒绝 | 差分门禁无法定义 |\n",
        "",
    )
    findings = _findings(tmp_path, "ADR-0024-notable.md", body)
    assert "alternatives_table_missing" in _signals(findings)


def test_adr_shape_alternatives_table_too_few_rows_is_reported(tmp_path):
    body = _WELL_FORMED_ADR.replace(
        "| C 双模双后端 | 拒绝 | 差分门禁无法定义 |\n", ""
    )
    findings = _findings(tmp_path, "ADR-0025-fewrows.md", body)
    assert "alternatives_table_too_few_rows" in _signals(findings)


def test_adr_shape_alternatives_table_without_conclusion_column_is_reported(tmp_path):
    """两列「备选 | 理由」把结论藏在正文措辞里 → 不可机读 ⇒ 缺结论列。"""
    body = _WELL_FORMED_ADR.replace(
        "| 备选 | 结论 | 理由 |\n|---|---|---|\n| A 保留双模 | 拒绝 | 模态开关带来二义 |\n"
        "| B 单模双后端 | 接受 | 模型唯一 |\n| C 双模双后端 | 拒绝 | 差分门禁无法定义 |\n",
        "| 备选 | 理由 |\n|---|---|\n| A 保留双模 | 模态开关带来二义 |\n"
        "| B 单模双后端 | 模型唯一 |\n| C 双模双后端 | 差分门禁无法定义 |\n",
    )
    findings = _findings(tmp_path, "ADR-0026-noconcl.md", body)
    assert "alternatives_table_no_conclusion_column" in _signals(findings)


def test_adr_shape_alternatives_table_conclusion_synonyms_are_accepted(tmp_path):
    """结论列用同义词（是否采用 / 决策 / 评估结果）也应当通过 —— 不能只认「结论」二字。"""
    body = _WELL_FORMED_ADR.replace(
        "| 备选 | 结论 | 理由 |\n|---|---|---|\n| A 保留双模 | 拒绝 | 模态开关带来二义 |\n"
        "| B 单模双后端 | 接受 | 模型唯一 |\n| C 双模双后端 | 拒绝 | 差分门禁无法定义 |\n",
        "| 方案 | 优点 | 缺点 | 是否采用 |\n|---|---|---|---|\n| A 保留双模 | x | y | 否 |\n"
        "| B 单模双后端 | x | y | 是 |\n| C 双模双后端 | x | y | 否 |\n",
    )
    findings = _findings(tmp_path, "ADR-0027-synonym.md", body)
    assert "alternatives_table_no_conclusion_column" not in _signals(findings)


def test_adr_shape_process_log_headings_are_reported(tmp_path):
    """本仓真实的漂移形态：过程/版本史 与 越界成 how-to 两类标题。"""
    for heading, signal in [
        ("## v3 修订日志（2026-09-24）", "process_log_heading"),
        ("## Implementation Status", "process_log_heading"),
        ("## Post-hoc Fix Record (2026-09-02)", "process_log_heading"),
        ("## Implementation", "shape_sprawl_heading"),
        ("## Test Strategy", "shape_sprawl_heading"),
        ("### 测试改动 (~7 个文件)", "shape_sprawl_heading"),
    ]:
        body = _WELL_FORMED_ADR + f"\n{heading}\n\n细节。\n"
        findings = _findings(tmp_path, f"ADR-0028-{signal}.md", body)
        assert signal in _signals(findings), f"{heading} should raise {signal}"


def test_adr_shape_prose_process_mention_is_not_a_heading_finding(tmp_path):
    """散文里提到「修订日志」不是标题级信号（自由文本族由既有正则另行覆盖）。"""
    body = _WELL_FORMED_ADR + "\n本 ADR 的前身有一段修订日志，此处仅作历史说明。\n"
    findings = _findings(tmp_path, "ADR-0029-prose.md", body)
    assert "process_log_heading" not in _signals(findings)


def test_adr_shape_findings_api_returns_structured_findings(tmp_path):
    body = _WELL_FORMED_ADR + "\n".join(f"- 推导行 {i}" for i in range(320))
    findings = _findings(tmp_path, "ADR-0030-big.md", body)
    assert findings, "expected findings for an oversized ADR"
    for f in findings:
        assert f.signal and f.file and f.detail
        assert f.file == "ADR-0030-big.md"


def test_adr_shape_reports_zero_files_scanned_instead_of_silent_pass(tmp_path):
    """扫描 0 份 ADR 必须显式报告，不能静默通过（假绿）。"""
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    findings = adr_shape_findings({"project_root": str(tmp_path)})
    assert "no_adr_files_scanned" in _signals(findings)


def test_adr_shape_cli_has_no_hardcoded_budget_defaults():
    """CLI 必须引用 Python 单一真源，不得内联复制判定逻辑或硬编码默认值。"""
    text = _SHAPE_CLI.read_text(encoding="utf-8")
    assert not re.search(r'"[0-9]{3}"', text), "CLI hardcodes a numeric default"
    assert "for line in lines" not in text, "CLI still duplicates the per-file scan loop"
    assert "adr_shape_findings" in text, "CLI must consume the Python findings API"
