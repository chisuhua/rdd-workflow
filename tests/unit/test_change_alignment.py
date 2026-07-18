"""Tests for change_alignment — qualitative checks for plan_done transition (ADR-0019).

ADR-0019 introduces 3 warning-level checks at plan_done:
  - change_adr_refs_valid    — design.md ADR refs resolve + status=accepted
  - change_no_contradiction  — anti-pattern keywords ADR-justified
  - change_task_traceability — ≥80% of tasks.md checkbox items reference ≥1 ADR

Plus STRICT_CHANGE_GATE=yes upgrade behavior (mirrors ADR-0018 pattern).

Tests follow Oracle review guidance (2026-07-10):
  - 12 MUST tests cover Critical/Important paths
  - 8 NICE tests cover edge cases + env var behavior
"""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from skills._lib.change_alignment import (
    _check_change_adr_refs_valid,
    _check_change_no_contradiction,
    _check_change_task_traceability,
    _resolve_active_change,
    ChangeAlignmentReport,
    ADRStatus,
    _classify_status_line,
    _TASK_ITEM_RE,
    _ANTI_PATTERNS,
)
from skills._lib.core.state_vector import StateVector


# ---------- Fixtures ----------


@pytest.fixture
def make_state_with_change():
    """Factory fixture to make a StateVector with a plan_side.active_change field."""
    def _make(change_name, also_arch=False):
        sv = StateVector.create_default()
        sv.update_field("plan_side.active_change", change_name)
        if also_arch:
            sv.update_field("arch_side.current_change", change_name)
        return sv
    return _make


@pytest.fixture
def project_with_accepted_adrs(tmp_path):
    """ADR with `✅ 已采纳` status (with emoji, Oracle A2 edge case)."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0007-gate.md").write_text(
        "# ADR-0007: 门控机制\n\n> **状态**: ✅ 已采纳\n\n## 背景\n\n...\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def project_with_replaced_adrs(tmp_path):
    """ADR with `已替代为 ADR-NNNN` status (Oracle A2)."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-old.md").write_text(
        "# ADR-0001\n\n> **状态**: 已替代为 ADR-0002 + ADR-0003\n",
        encoding="utf-8",
    )
    (adr_dir / "ADR-0007-gate.md").write_text(
        "# ADR-0007\n\n> **状态**: 已采纳\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def project_with_deprecated_adrs(tmp_path):
    """ADR with `已弃用` status (Oracle A2)."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0005-deprecated.md").write_text(
        "# ADR-0005\n\n> **状态**: 已弃用\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def project_with_change_no_design(tmp_path):
    """Project with active change but no design.md (Oracle A5 defense test)."""
    change_dir = tmp_path / "openspec" / "changes" / "test-change"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text("# Proposal\n", encoding="utf-8")
    return tmp_path


def _ctx_for(project_root, state_vector=None):
    ctx = {"project_root": str(project_root)}
    if state_vector is not None:
        ctx["state_vector"] = state_vector
    return ctx


# ============================================================
# MUST Tests (12)
# ============================================================


# --- change_adr_refs_valid ---


def test_adr_refs_valid_all_adopted(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """All references in design.md point to accepted ADRs → pass."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-x"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\n依据 ADR-0007 §3 我们采用门控机制。\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-x")
    passed, severity = _check_change_adr_refs_valid(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is True
    assert severity is None


def test_adr_refs_valid_references_deprecated(make_state_with_change, project_with_deprecated_adrs, tmp_path):
    """design.md references a deprecated ADR → warning."""
    change_dir = project_with_deprecated_adrs / "openspec" / "changes" / "feat-y"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\n依据 ADR-0005 实现。\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-y")
    passed, severity = _check_change_adr_refs_valid(_ctx_for(project_with_deprecated_adrs, sv))
    assert passed is False
    assert severity == "warning"


def test_adr_refs_valid_references_superseded(make_state_with_change, project_with_replaced_adrs, tmp_path):
    """design.md references a replaced ADR (e.g., ADR-0001) → warning."""
    change_dir = project_with_replaced_adrs / "openspec" / "changes" / "feat-z"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\n依据 ADR-0001 实现。\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-z")
    passed, severity = _check_change_adr_refs_valid(_ctx_for(project_with_replaced_adrs, sv))
    assert passed is False
    assert severity == "warning"


def test_adr_refs_valid_emoji_status(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """design.md references ADR with `✅ 已采纳` (emoji variant) → pass."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-emoji"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\n依据 ADR-0007 §2 实现。\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-emoji")
    passed, severity = _check_change_adr_refs_valid(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is True
    assert severity is None


def test_adr_refs_valid_no_design_md(make_state_with_change, project_with_change_no_design):
    """design.md missing → pass (Oracle A5 defense; artifacts_complete covers existence)."""
    sv = make_state_with_change("test-change")
    passed, severity = _check_change_adr_refs_valid(_ctx_for(project_with_change_no_design, sv))
    assert passed is True
    assert severity is None


# --- change_no_contradiction ---


def test_no_contradiction_clean(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """design.md without anti-pattern keywords → pass."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-clean"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\n依据 ADR-0007 实现完整门控流程。\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-clean")
    passed, severity = _check_change_no_contradiction(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is True
    assert severity is None


def test_no_contradiction_with_adr_ref(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """design.md contains warn-level anti-pattern BUT also cites ADR → pass (justified)."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-justified"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\n跳过架构阶段（依据 ADR-0007 §2 紧急修复）。\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-justified")
    passed, severity = _check_change_no_contradiction(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is True
    assert severity is None


def test_no_contradiction_warn_severity_no_adr(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """design.md contains `跳过架构` WITHOUT any ADR ref → warning."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-skip"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\n为了紧急发布，我们将跳过架构审查。\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-skip")
    passed, severity = _check_change_no_contradiction(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is False
    assert severity == "warning"


# --- change_task_traceability ---


def test_task_traceability_80_pct(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """Exactly 80% of tasks have ADR refs → pass."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-80"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n"
        "- [ ] 1.1 实现门控 (ADR-0007 §2)\n"
        "- [ ] 1.2 编写测试 (ADR-0007 §3)\n"
        "- [ ] 1.3 文档更新 (ADR-0007 §4)\n"
        "- [ ] 1.4 部署 (ADR-0007 §4)\n"
        "- [ ] 1.5 通知\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-80")
    passed, severity = _check_change_task_traceability(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is True
    assert severity is None


def test_task_traceability_below_80(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """Only 75% have ADR refs → warning."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-low"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n"
        "- [ ] 1.1 实现门控 (ADR-0007 §2)\n"
        "- [ ] 1.2 编写测试\n"
        "- [ ] 1.3 文档更新\n"
        "- [ ] 1.4 部署\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-low")
    passed, severity = _check_change_task_traceability(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is False
    assert severity == "warning"


def test_task_traceability_empty_tasks(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """Empty tasks.md → pass (Oracle A5: no tasks = no check)."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-empty"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text("# Tasks\n\n(empty)\n", encoding="utf-8")
    sv = make_state_with_change("feat-empty")
    passed, severity = _check_change_task_traceability(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is True
    assert severity is None


def test_task_traceability_checkbox_format(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """`- [ ]` and `- [x]` both parsed; section headers ignored."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-check"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n"
        "## 1. Schema 准备\n"
        "- [ ] 1.1 字段定义 (ADR-0007 §3)\n"
        "- [x] 1.2 测试 (ADR-0007 §3)\n"
        "\n"
        "## 2. 实现\n"
        "- [ ] 2.1 API (ADR-0007 §2)\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-check")
    passed, severity = _check_change_task_traceability(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is True
    assert severity is None


# ============================================================
# NICE Tests (8)
# ============================================================


def test_no_contradiction_info_severity_no_adr(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """info-level anti-pattern without ADR ref → still pass (only warn blocks)."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-info"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\n为简化实现，我们临时采用单阶段状态机。\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-info")
    passed, severity = _check_change_no_contradiction(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is True
    assert severity is None


def test_adr_refs_valid_self_reference_adr0018(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """design.md references ADR-0018 (the predecessor ADR) → pass."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-meta"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\n依据 ADR-0018 实现 change alignment 检查。\n",
        encoding="utf-8",
    )
    (project_with_accepted_adrs / "docs" / "adr" / "ADR-0018-arch-quality-gate.md").write_text(
        "# ADR-0018\n\n> **状态**: ✅ 已采纳\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-meta")
    passed, severity = _check_change_adr_refs_valid(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is True
    assert severity is None


def test_task_traceability_no_checkbox_format(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """tasks.md with pure bullets (no checkboxes) → pass (no traceable items counted)."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-bullet"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n"
        "- 实现门控 (ADR-0007)\n"
        "- 编写测试\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-bullet")
    passed, severity = _check_change_task_traceability(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is True
    assert severity is None


def test_strict_change_gate_upgrades_warning(make_state_with_change, project_with_accepted_adrs, tmp_path, monkeypatch):
    """STRICT_CHANGE_GATE=yes upgrades warning to error in registration layer."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-strict"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] 1.1 no ref here\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-strict")
    monkeypatch.setenv("STRICT_CHANGE_GATE", "yes")
    from skills._lib.arch_quality_gate import strict_wrap
    wrapped = strict_wrap(_check_change_task_traceability, env_var="STRICT_CHANGE_GATE")
    passed, severity = wrapped(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is False
    assert severity == "error"


def test_strict_change_gate_off_keeps_warning(make_state_with_change, project_with_accepted_adrs, tmp_path, monkeypatch):
    """STRICT_CHANGE_GATE off keeps warning as warning."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-lax"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] 1.1 no ref\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-lax")
    monkeypatch.delenv("STRICT_CHANGE_GATE", raising=False)
    from skills._lib.arch_quality_gate import strict_wrap
    wrapped = strict_wrap(_check_change_task_traceability, env_var="STRICT_CHANGE_GATE")
    passed, severity = wrapped(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is False
    assert severity == "warning"


def test_change_name_from_plan_side(make_state_with_change):
    """Reads plan_side.active_change (plan semantics)."""
    sv = make_state_with_change("plan-change")
    name = _resolve_active_change({"state_vector": sv})
    assert name == "plan-change"


def test_change_name_from_arch_side_fallback():
    """Falls back to arch_side.current_change if plan_side not set."""
    sv = StateVector.create_default()
    sv.update_field("arch_side.current_change", "arch-change")
    name = _resolve_active_change({"state_vector": sv})
    assert name == "arch-change"


def test_anti_pattern_case_insensitive(make_state_with_change, project_with_accepted_adrs, tmp_path):
    """Anti-pattern regex is case-insensitive."""
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-case"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\nWe will Hard-Code the values.\n",
        encoding="utf-8",
    )
    sv = make_state_with_change("feat-case")
    passed, severity = _check_change_no_contradiction(_ctx_for(project_with_accepted_adrs, sv))
    assert passed is True
    assert severity is None


# ============================================================
# Unit tests for helpers
# ============================================================


def test_classify_status_line_emoji():
    """`✅ 已采纳` classified as ACCEPTED (Oracle A2)."""
    assert _classify_status_line("✅ 已采纳") == ADRStatus.ACCEPTED


def test_classify_status_line_replaced():
    """`已替代为 ADR-NNN` classified as REPLACED."""
    assert _classify_status_line("已替代为 ADR-0002 + ADR-0003") == ADRStatus.REPLACED


def test_classify_status_line_deprecated():
    assert _classify_status_line("已弃用") == ADRStatus.DEPRECATED


def test_classify_status_line_pending():
    assert _classify_status_line("待定") == ADRStatus.PENDING


def test_classify_status_line_unknown():
    assert _classify_status_line("some unknown text") == ADRStatus.UNKNOWN


def test_task_item_regex_matches_checkboxes():
    text = "- [ ] task one\n- [x] task two\n- [X] task three\n"
    matches = _TASK_ITEM_RE.findall(text)
    assert matches == ["task one", "task two", "task three"]


def test_task_item_regex_ignores_section_headers():
    text = "## 1. Header\n- [ ] task\n"
    matches = _TASK_ITEM_RE.findall(text)
    assert matches == ["task"]


def test_anti_patterns_three_total():
    """Oracle 2026-07-10: keep v1 at 3 conservative patterns."""
    assert len(_ANTI_PATTERNS) == 3


# ============================================================
# ChangeAlignmentReport aggregator
# ============================================================


def test_change_alignment_report_aggregator_passes(make_state_with_change, project_with_accepted_adrs, tmp_path, monkeypatch):
    """Report aggregates all 3 checks."""
    monkeypatch.delenv("STRICT_CHANGE_GATE", raising=False)
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-agg"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\n依据 ADR-0007 §2 实现门控。\n",
        encoding="utf-8",
    )
    (change_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] 1.1 task (ADR-0007 §2)\n",
        encoding="utf-8",
    )
    report = ChangeAlignmentReport.verify(str(project_with_accepted_adrs), change_name="feat-agg")
    assert report.passed is True
    assert report.warnings == []


def test_change_alignment_report_collects_warnings(make_state_with_change, project_with_accepted_adrs, tmp_path, monkeypatch):
    """Report surfaces change_no_contradiction warning when applicable."""
    monkeypatch.delenv("STRICT_CHANGE_GATE", raising=False)
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-warn"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text(
        "# Design\n\n为了紧急发布，我们将跳过架构审查。\n",
        encoding="utf-8",
    )
    report = ChangeAlignmentReport.verify(str(project_with_accepted_adrs), change_name="feat-warn")
    assert "change_no_contradiction" in report.warnings


def test_change_alignment_report_strict_mode_flag(make_state_with_change, project_with_accepted_adrs, tmp_path, monkeypatch):
    """Report carries strict_mode flag for observability."""
    monkeypatch.setenv("STRICT_CHANGE_GATE", "yes")
    change_dir = project_with_accepted_adrs / "openspec" / "changes" / "feat-flag"
    change_dir.mkdir(parents=True)
    (change_dir / "design.md").write_text("# Clean design\n", encoding="utf-8")
    report = ChangeAlignmentReport.verify(str(project_with_accepted_adrs), change_name="feat-flag")
    assert report.strict_mode is True