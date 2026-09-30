"""Tests for arch_audit_check (cat-arch-audit).

Covers all 3 sub-checks (per ADR-0057, gap-analysis replaced by theme-doc check):
  1. Theme-doc inventory summary (per ADR-0057: rdd-arch owns docs/architecture/*.md)
  2. ADR inventory summary + status drift detection
  3. arch-handoff.json sanity
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Finding, Severity  # noqa: E402
from checks.arch_audit_check import (  # noqa: E402
    _CATEGORY,
    _check_adr_inventory,
    _check_arch_handoff,
    _check_theme_docs,
    run as run_check,
)


# ---------------------------------------------------------------------------
# Theme-doc sub-check (per ADR-0057; replaces gap-analysis check)
# ---------------------------------------------------------------------------

def test_theme_check_no_arch_dir_returns_warning(tmp_path: Path):
    """docs/architecture/ missing → WARNING (rdd-arch owns theme docs per ADR-0057)."""
    findings = _check_theme_docs(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert "docs/architecture/ missing" in findings[0].snippet


def test_theme_check_empty_dir_returns_warning(tmp_path: Path):
    """docs/architecture/ exists but no theme docs → WARNING (no architecture snapshot)."""
    (tmp_path / "docs" / "architecture").mkdir(parents=True)
    findings = _check_theme_docs(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.WARNING
    assert "0 theme docs found" in findings[0].snippet


def test_theme_check_with_docs_returns_summary(tmp_path: Path):
    """Multiple theme docs → INFO summary listing up to 5 names."""
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir(parents=True)
    (arch_dir / "overview.md").write_text("# Overview\n")
    (arch_dir / "workflow-phases.md").write_text("# Workflow\n")
    # Template file should be excluded
    (arch_dir / "README-0000-template.md").write_text("# template\n")
    findings = _check_theme_docs(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == Severity.INFO
    assert "2 theme docs" in findings[0].snippet
    assert "overview" in findings[0].snippet
    assert "workflow-phases" in findings[0].snippet
    # Template excluded
    assert "template" not in findings[0].snippet


def test_theme_check_truncates_long_list(tmp_path: Path):
    """More than 5 theme docs → summary truncates with ellipsis."""
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir(parents=True)
    for i in range(7):
        (arch_dir / f"topic-{i}.md").write_text(f"# Topic {i}\n")
    findings = _check_theme_docs(tmp_path)
    snippet = findings[0].snippet
    assert "7 theme docs" in snippet
    assert "…" in snippet


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
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-foo.md").write_text("# ADR-0001\n\n> **状态**: 已采纳\n\nx.\n")
    findings = run_check(project_root=tmp_path)
    categories = {f.category for f in findings}
    assert categories == {_CATEGORY}
    severities = [f.severity for f in findings]
    # Has WARNING (theme-docs missing) + INFO (ADR + handoff)
    assert Severity.WARNING in severities
    assert Severity.INFO in severities


def test_run_handles_missing_project_root_env(tmp_path: Path, monkeypatch):
    """run() resolves project_root from RDDF_PROJECT_ROOT env var."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings = run_check(project_root=None)
    assert len(findings) >= 2


def test_run_with_healthy_project_returns_only_info(tmp_path: Path):
    """Healthy project (ADR + theme docs + valid handoff) → no WARNING/CRITICAL."""
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "ADR-0001-foo.md").write_text(
        "# ADR-0001\n\n> **状态**: 已采纳\n\nx.\n"
    )
    arch_dir = tmp_path / "docs" / "architecture"
    arch_dir.mkdir(parents=True)
    (arch_dir / "overview.md").write_text("# Overview\n\nCurrent state description.\n")
    state = tmp_path / ".rddf" / "state"
    state.mkdir(parents=True)
    (state / ".arch-handoff.json").write_text(json.dumps({
        "version": 2, "adr_count": 1, "arch_complete_at": "2026-09-29T00:00:00Z",
    }))
    findings = run_check(project_root=tmp_path)
    severities = {f.severity for f in findings}
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