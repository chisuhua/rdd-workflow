"""Tests for arch_audit_check (cat-arch-audit).

Covers all 3 sub-checks:
  1. Gap-analysis structural_ok / completeness (via _lib.arch.protocol.validate_document)
  2. ADR inventory summary + status drift detection
  3. arch-handoff.json sanity
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Mirror the sys.path injection pattern from test_state_schema_check.py
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Finding, Severity  # noqa: E402
from checks.arch_audit_check import (  # noqa: E402
    _CATEGORY,
    _check_adr_inventory,
    _check_arch_handoff,
    _check_gap_analyses,
    run as run_check,
)


# ---------------------------------------------------------------------------
# Gap-analysis sub-check
# ---------------------------------------------------------------------------

def test_gap_check_no_arch_dir_returns_info(tmp_path: Path):
    """docs/architecture/ missing → INFO (no-op, not failure)."""
    findings = _check_gap_analyses(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "docs/architecture/ missing" in findings[0].snippet


def test_gap_check_empty_dir_returns_info(tmp_path: Path):
    """docs/architecture/ exists but no gap-analysis files → INFO."""
    (tmp_path / "docs" / "architecture").mkdir(parents=True)
    findings = _check_gap_analyses(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "0 gap-analyses found" in findings[0].snippet


def test_gap_check_complete_returns_info(tmp_path: Path):
    """Complete gap-analysis (all 5 sections, no placeholders) → INFO."""
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir(parents=True)
    gap = arch_dir / "test-gap-analysis.md"
    gap.write_text(
        "# 架构差距分析: test\n\n"
        "## 1. 目标架构\n\nFilled target.\n\n"
        "## 2. 当前架构\n\nFilled current.\n\n"
        "## 3. 差距清单\n\n| 1 | x | 高 | P0 | change |\n\n"
        "## 4. 补齐路径\n\nSteps.\n\n"
        "## 5. 参考资料\n\n- ADR-0001\n"
    )
    findings = _check_gap_analyses(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "complete" in findings[0].snippet


def test_gap_check_draft_returns_info_with_draft_label(tmp_path: Path):
    """Skeleton-only (all placeholders intact) → INFO with draft label."""
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir(parents=True)
    gap = arch_dir / "draft-gap-analysis.md"
    # Mirror the skeleton template from _lib/arch/protocol.py
    gap.write_text(
        "# 架构差距分析: draft\n\n"
        "## 1. 目标架构\n\n(描述 ADR 中定义的目标架构)\n\n"
        "## 2. 当前架构\n\n(描述项目当前实际架构)\n\n"
        "## 3. 差距清单\n\n"
        "| # | 差距项 | 严重程度 | 优先级 | 关联 change |\n"
        "|---|--------|---------|--------|------------|\n"
        "| 1 | ... | 高/中/低 | P0/P1/P2 | ... |\n\n"
        "## 4. 补齐路径\n\n(描述从当前架构迁移到目标架构的步骤、顺序、依赖)\n\n"
        "## 5. 参考资料\n\n- 相关 ADR\n- 相关 change artifacts\n"
    )
    findings = _check_gap_analyses(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "draft" in findings[0].snippet
    assert "skeleton" in findings[0].snippet


def test_gap_check_structural_drift_returns_warning(tmp_path: Path):
    """File present but missing required sections → WARNING (structural_ok=False)."""
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir(parents=True)
    gap = arch_dir / "broken-gap-analysis.md"
    gap.write_text("# Broken\n\n## Random Section\n\nNothing useful.\n")
    findings = _check_gap_analyses(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert "structural drift" in findings[0].snippet
    # Per ADR-0046 §5, structural_ok failures are HARD; we surface WARNING
    # because arch-audit is advisory (never blocks gates).


def test_gap_check_multiple_files(tmp_path: Path):
    """Multiple gap-analyses: each gets its own finding."""
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir(parents=True)
    # File 1: complete
    (arch_dir / "a-gap-analysis.md").write_text(
        "# 架构差距分析: a\n\n"
        "## 1. 目标架构\n\nx\n\n## 2. 当前架构\n\nx\n\n"
        "## 3. 差距清单\n\n| 1 | x | 高 | P0 | x |\n\n"
        "## 4. 补齐路径\n\nx\n\n## 5. 参考资料\n\n- x\n"
    )
    # File 2: broken
    (arch_dir / "b-gap-analysis.md").write_text("# B\n\nbroken.\n")
    findings = _check_gap_analyses(tmp_path)
    assert len(findings) == 2
    severities = {f.severity for f in findings}
    assert Severity.WARNING in severities
    assert Severity.INFO in severities


# ---------------------------------------------------------------------------
# ADR inventory sub-check
# ---------------------------------------------------------------------------

def test_adr_inventory_no_dir_returns_info(tmp_path: Path):
    """docs/adr/ missing → INFO."""
    findings = _check_adr_inventory(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "docs/adr/ missing" in findings[0].snippet


def test_adr_inventory_empty_dir_returns_info(tmp_path: Path):
    """docs/adr/ exists but no ADRs → INFO."""
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    findings = _check_adr_inventory(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "0 ADRs found" in findings[0].snippet


def test_adr_inventory_with_adrs_returns_summary(tmp_path: Path):
    """Multiple ADRs → INFO summary with count, latest, superseded."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-foo.md").write_text(
        "# ADR-0001\n\n> **状态**: 已采纳\n\nContent.\n"
    )
    (adr_dir / "ADR-0002-bar.md").write_text(
        "# ADR-0002\n\n> **状态**: Superseded\n\nContent.\n"
    )
    (adr_dir / "ADR-0003-baz.md").write_text(
        "# ADR-0003\n\n> **状态**: 已采纳\n\nContent.\n"
    )
    # Template file should be excluded
    (adr_dir / "ADR-0000-template.md").write_text("# template\n")
    findings = _check_adr_inventory(tmp_path)
    summary = next(f for f in findings if "ADRs" in f.snippet and "latest" in f.snippet)
    assert summary.severity == Severity.INFO
    assert "3 ADRs" in summary.snippet
    assert "ADR-0003" in summary.snippet
    assert "superseded: 1" in summary.snippet


def test_adr_inventory_status_drift_returns_warning(tmp_path: Path):
    """ADR with non-terminal status (待定 / Draft / Proposed) → WARNING."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-pending.md").write_text(
        "# ADR-0001\n\n> **状态**: 待定\n\nContent.\n"
    )
    findings = _check_adr_inventory(tmp_path)
    drift_warnings = [f for f in findings if f.severity == Severity.WARNING]
    assert len(drift_warnings) == 1
    assert "non-terminal" in drift_warnings[0].snippet


def test_adr_inventory_superseded_detection(tmp_path: Path):
    """ADR with Superseded / 替代 status increments superseded counter."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-old.md").write_text(
        "# ADR-0001\n\n> **状态**: Superseded by ADR-0002\n\nOld.\n"
    )
    findings = _check_adr_inventory(tmp_path)
    summary = next(f for f in findings if "ADRs" in f.snippet)
    assert "superseded: 1" in summary.snippet


# ---------------------------------------------------------------------------
# arch-handoff sub-check
# ---------------------------------------------------------------------------

def test_handoff_missing_returns_info(tmp_path: Path):
    """.rddf/state/.arch-handoff.json missing → INFO (expected pre-Phase-1)."""
    findings = _check_arch_handoff(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "arch-handoff missing" in findings[0].snippet


def test_handoff_invalid_json_returns_critical(tmp_path: Path):
    """Malformed JSON in handoff → CRITICAL (real bug surface)."""
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    (state / ".arch-handoff.json").write_text("{not valid json")
    findings = _check_arch_handoff(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert "invalid JSON" in findings[0].snippet


def test_handoff_unknown_version_returns_warning(tmp_path: Path):
    """version=99 (not 1 or 2) → WARNING."""
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    (state / ".arch-handoff.json").write_text(json.dumps({"version": 99}))
    findings = _check_arch_handoff(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert "unknown schema version" in findings[0].snippet


def test_handoff_v1_valid_returns_info(tmp_path: Path):
    """Valid v1 handoff → INFO summary."""
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    (state / ".arch-handoff.json").write_text(json.dumps({
        "version": 1,
        "adr_count": 5,
        "arch_complete_at": "2026-08-15T16:40:59Z",
    }))
    findings = _check_arch_handoff(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "v1" in findings[0].snippet
    assert "adr_count=5" in findings[0].snippet


def test_handoff_v2_valid_returns_info(tmp_path: Path):
    """Valid v2 handoff → INFO summary."""
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    (state / ".arch-handoff.json").write_text(json.dumps({
        "version": 2,
        "adr_count": 10,
        "arch_complete_at": "2026-09-01T00:00:00Z",
    }))
    findings = _check_arch_handoff(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "v2" in findings[0].snippet


# ---------------------------------------------------------------------------
# Aggregate run() entry point
# ---------------------------------------------------------------------------

def test_run_aggregates_all_three_subchecks(tmp_path: Path):
    """run() returns findings from all 3 sub-checks (none raise)."""
    # Minimal fixture: ADRs present, no gap-analyses, no handoff
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-foo.md").write_text("# ADR-0001\n\n> **状态**: 已采纳\n\nx.\n")
    findings = run_check(project_root=tmp_path)
    # 1 ADR inventory INFO + 1 arch-handoff missing INFO = 2 findings
    categories = {f.category for f in findings}
    assert categories == {_CATEGORY}
    severities = [f.severity for f in findings]
    # All findings should be INFO (nothing broken)
    assert all(s == Severity.INFO for s in severities)


def test_run_handles_missing_project_root_env(tmp_path: Path, monkeypatch):
    """run() resolves project_root from RDDF_PROJECT_ROOT env var."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    # Empty tmp_path → all 3 sub-checks return INFO (no failures)
    findings = run_check(project_root=None)
    assert len(findings) >= 2  # at least ADR inventory + arch-handoff missing


def test_run_with_complete_project_returns_info_only(tmp_path: Path):
    """Healthy project → no WARNING/CRITICAL from arch-audit."""
    # ADRs
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-foo.md").write_text(
        "# ADR-0001\n\n> **状态**: 已采纳\n\nx.\n"
    )
    # Complete gap-analysis
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir(parents=True)
    (arch_dir / "test-gap-analysis.md").write_text(
        "# 架构差距分析: test\n\n"
        "## 1. 目标架构\n\nx\n\n## 2. 当前架构\n\nx\n\n"
        "## 3. 差距清单\n\n| 1 | x | 高 | P0 | x |\n\n"
        "## 4. 补齐路径\n\nx\n\n## 5. 参考资料\n\n- x\n"
    )
    # Valid v2 handoff
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    (state / ".arch-handoff.json").write_text(json.dumps({
        "version": 2, "adr_count": 1, "arch_complete_at": "2026-09-29T00:00:00Z",
    }))
    findings = run_check(project_root=tmp_path)
    severities = {f.severity for f in findings}
    # Healthy fixture → only INFO (no WARNING, no CRITICAL)
    assert Severity.CRITICAL not in severities
    assert Severity.WARNING not in severities
    assert Severity.INFO in severities


# ---------------------------------------------------------------------------
# Module contract
# ---------------------------------------------------------------------------

def test_module_category_constant():
    """All findings must use the 'arch-audit' category for filtering."""
    assert _CATEGORY == "arch-audit"


def test_run_returns_list_of_finding():
    """Sanity: run() returns list[Finding]."""
    import os
    findings = run_check(project_root=Path(os.environ.get("TMPDIR", "/tmp")))
    assert isinstance(findings, list)
    for f in findings:
        assert isinstance(f, Finding)