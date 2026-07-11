"""Tests for arch_quality_gate — qualitative arch-done checks beyond structural existence.

ADR-0013 introduces 4 warning-level checks that run on arch_done transition:
  - arch_alignment       — ADR/roadmap/gap-analysis cross-references resolve
  - arch_debt_recorded   — gap-analysis has no unresolved high-priority items
  - adr_no_placeholders  — ADR files are not template stubs
  - arch_handoff_actionable — .arch-handoff.json carries actionable fields for guide-plan

These checks default to severity="warning" (allow transition but record).
STRICT_ARCH_GATE=yes env var upgrades warnings to errors for CI.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

import pytest

from skills._lib.arch_quality_gate import (
    _check_arch_alignment,
    _check_arch_debt,
    _check_adr_clarity,
    _check_handoff_actionable,
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

    # Gap analysis referencing real ADRs, no unresolved high-priority
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir()
    (arch_dir / "v2-migration-gap-analysis.md").write_text(
        "# 架构差距分析: v2 迁移\n\n"
        "> **关联 ADR**: ADR-0001\n\n"
        "## 3. 差距清单\n\n"
        "| # | 差距项 | 严重程度 | 优先级 | 关联 change |\n"
        "|---|--------|---------|--------|------------|\n"
        "| 1 | 拆分状态机 | 中 | P1 | openspec/split-statemachine |\n",
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
def project_with_unresolved_debt(tmp_path):
    """gap-analysis has unresolved high-severity / P0 row."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-test.md").write_text("# ADR-0001\n\n## 状态\n\n已采纳\n", encoding="utf-8")

    roadmap = tmp_path / "roadmap.md"
    roadmap.write_text("**当前阶段**: phase-1\n", encoding="utf-8")

    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir()
    (arch_dir / "critical-gap-analysis.md").write_text(
        "# 差距分析\n\n"
        "> **关联 ADR**: ADR-0001\n\n"
        "## 3. 差距清单\n\n"
        "| # | 差距项 | 严重程度 | 优先级 | 关联 change |\n"
        "|---|--------|---------|--------|------------|\n"
        "| 1 | 安全关键 | 高 | P0 | (待补充) |\n",
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


def test_arch_alignment_warns_on_ghost_adr_in_gap_analysis(tmp_path):
    """gap-analysis references a non-existent ADR → warning."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-real.md").write_text("# ADR-0001\n\n## 状态\n\n已采纳\n", encoding="utf-8")
    (tmp_path / "roadmap.md").write_text("**当前阶段**: phase-1\n", encoding="utf-8")
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir()
    (arch_dir / "ghost-ref-gap-analysis.md").write_text(
        "# g\n\n> **关联 ADR**: ADR-1234 (ghost)\n\n"
        "## 3. 差距清单\n\n| # | x | 中 | P1 | done |\n",
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


# ---------- 2. debt ----------

def test_arch_debt_passes_when_no_p0_unresolved(project_with_clean_arch):
    """No unresolved P0/high row in any gap-analysis → pass."""
    passed, severity = _check_arch_debt(_ctx(project_with_clean_arch))
    assert passed is True
    assert severity is None


def test_arch_debt_warns_on_p0_unresolved(project_with_unresolved_debt):
    """A '高 / P0 / (待补充)' row → warning."""
    passed, severity = _check_arch_debt(_ctx(project_with_unresolved_debt))
    assert passed is False
    assert severity == "warning"


def test_arch_debt_handles_no_gap_analysis(tmp_path):
    """When arch_dir empty or missing → pass (debt detection is opt-in)."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001.md").write_text("# ADR-0001\n", encoding="utf-8")
    (tmp_path / "roadmap.md").write_text("**当前阶段**: phase-1\n", encoding="utf-8")
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

    passed, severity = _check_arch_debt(_ctx(tmp_path))
    assert passed is True
    assert severity is None


# ---------- 3. clarity ----------

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


# ---------- 4. handoff actionable ----------

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