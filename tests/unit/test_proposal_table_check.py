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
    (tmp_path / ".rddf/improvements").mkdir(parents=True)
    (tmp_path / ".rddf/improvements" / "foo.md").write_text("# foo\n")
    (tmp_path / "proposal-suggestions.md").write_text(
        "# 提案池\n\n"
        "| 提案 | 优先级 | 来源 | 添加时间 | 状态 |\n"
        "|------|--------|------|----------|------|\n"
        "| [foo](.rddf/improvements/foo.md) | P1 | src | 2026-08-07 | 待审 |\n"
    )
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_column_count_drift_reports_warning(tmp_path: Path):
    (tmp_path / "proposal-suggestions.md").write_text(
        "| 提案 | 优先级 | 来源 | 添加时间 |\n"  # missing 状态 column
        "|------|--------|------|----------|\n"
        "| [foo](.rddf/improvements/foo.md) | P1 | src | 2026-08-07 |\n"
    )
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING for f in findings)
    assert any("4 columns" in f.snippet or "5" in f.snippet for f in findings)


def test_broken_link_reports_warning(tmp_path: Path):
    (tmp_path / "proposal-suggestions.md").write_text(
        "| 提案 | 优先级 | 来源 | 添加时间 | 状态 |\n"
        "|------|--------|------|----------|------|\n"
        "| [foo](.rddf/improvements/nonexistent.md) | P1 | src | 2026-08-07 | 待审 |\n"
    )
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING for f in findings)
    assert any("nonexistent" in f.snippet for f in findings)


def test_no_proposal_files_returns_no_findings(tmp_path: Path):
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_well_formed_proposal_approved(tmp_path: Path):
    (tmp_path / "proposal-approved.md").write_text(
        "| [foo](.rddf/improvements/foo.md) | P1 | 2026-08-07 |\n"
    )
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_legacy_top_level_improvements_link_reports_warning(tmp_path: Path):
    """Gap 2 regression: proposal-suggestions.md and proposal-approved.md
    must use canonical `.rddf/improvements/<name>.md` links. Legacy
    `improvements/<name>.md` (top-level) format is rejected even when the
    target file happens to exist (post-migration naming contract)."""
    (tmp_path / "improvements").mkdir()
    (tmp_path / "improvements" / "legacy-name.md").write_text("# legacy\n")
    (tmp_path / ".rddf/improvements").mkdir(parents=True)
    (tmp_path / ".rddf/improvements" / "canonical-name.md").write_text("# canonical\n")
    (tmp_path / "proposal-suggestions.md").write_text(
        "# 提案池\n\n"
        "| 提案 | 优先级 | 来源 | 添加时间 | 状态 |\n"
        "|------|--------|------|----------|------|\n"
        "| [legacy-name](improvements/legacy-name.md) | P1 | src | 2026-08-13 | 待审 |\n"
        "| [canonical-name](.rddf/improvements/canonical-name.md) | P1 | src | 2026-08-13 | 待审 |\n"
    )
    (tmp_path / "proposal-approved.md").write_text(
        "# 已批准提案\n\n"
        "| 提案 | 优先级 | 批准时间 | 批准者 |\n"
        "|------|--------|----------|--------|\n"
        "| [legacy-name](improvements/legacy-name.md) | P1 | 2026-08-13 | manual |\n"
    )
    findings = run_check(project_root=tmp_path)
    legacy_findings = [
        f for f in findings
        if "improvements/legacy-name.md" in f.snippet
        and "non-canonical" in f.snippet.lower()
    ]
    assert len(legacy_findings) >= 2, (
        f"expected at least 2 non-canonical warnings (1 per file), got "
        f"{len(legacy_findings)}: {[f.snippet for f in findings]}"
    )