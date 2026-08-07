"""Tests for proposal_table_check (cat-4)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from checks.proposal_table_check import run as run_check  # noqa: E402


def test_well_formed_proposal_suggestions_returns_no_findings(tmp_path: Path):
    (tmp_path / "improvements").mkdir()
    (tmp_path / "improvements" / "foo.md").write_text("# foo\n")
    (tmp_path / "proposal-suggestions.md").write_text(
        "# 提案池\n\n"
        "| 提案 | 优先级 | 来源 | 添加时间 | 状态 |\n"
        "|------|--------|------|----------|------|\n"
        "| [foo](improvements/foo.md) | P1 | src | 2026-08-07 | 待审 |\n"
    )
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_column_count_drift_reports_warning(tmp_path: Path):
    (tmp_path / "proposal-suggestions.md").write_text(
        "| 提案 | 优先级 | 来源 | 添加时间 |\n"  # missing 状态 column
        "|------|--------|------|----------|\n"
        "| [foo](improvements/foo.md) | P1 | src | 2026-08-07 |\n"
    )
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING for f in findings)
    assert any("4 columns" in f.snippet or "5" in f.snippet for f in findings)


def test_broken_link_reports_warning(tmp_path: Path):
    (tmp_path / "proposal-suggestions.md").write_text(
        "| 提案 | 优先级 | 来源 | 添加时间 | 状态 |\n"
        "|------|--------|------|----------|------|\n"
        "| [foo](improvements/nonexistent.md) | P1 | src | 2026-08-07 | 待审 |\n"
    )
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING for f in findings)
    assert any("nonexistent" in f.snippet for f in findings)


def test_no_proposal_files_returns_no_findings(tmp_path: Path):
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_well_formed_proposal_approved(tmp_path: Path):
    (tmp_path / "proposal-approved.md").write_text(
        "| [foo](improvements/foo.md) | P1 | 2026-08-07 |\n"
    )
    findings = run_check(project_root=tmp_path)
    assert findings == []