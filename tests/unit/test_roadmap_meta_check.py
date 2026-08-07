"""Tests for roadmap_meta_check (cat-3) — S4 root cause path."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from checks.roadmap_meta_check import run as run_check  # noqa: E402


def _make_change(tmp_path: Path, name: str, roadmap_content: str) -> None:
    change_dir = tmp_path / "openspec" / "changes" / name
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "roadmap-meta.yaml").write_text(roadmap_content)


def test_healthy_roadmap_no_findings(tmp_path: Path):
    _make_change(tmp_path, "foo", """\
phase: v2.1
category: infra-setup
change_type: feature
priority: P1
parent_feature: ""
""")
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_manual_deps_string_drifts_reports_critical_with_silently_ignore(tmp_path: Path):
    """S4 root cause: deps stage silently skips this drift. Doctor must catch it."""
    _make_change(tmp_path, "foo", """\
phase: v2.1
category: infra-setup
change_type: feature
priority: P1
parent_feature: ""
manual_deps: "x,y"
manual_blocks: []
""")
    findings = run_check(project_root=tmp_path)
    critical = [f for f in findings if f.severity == Severity.CRITICAL]
    assert len(critical) == 1
    assert "silently ignore" in critical[0].fix_hint
    assert "manual_deps" in critical[0].snippet


def test_manual_blocks_string_drifts_reports_critical(tmp_path: Path):
    _make_change(tmp_path, "foo", """\
phase: v2.1
category: infra-setup
change_type: feature
priority: P1
parent_feature: ""
manual_deps: []
manual_blocks: "a,b"
""")
    findings = run_check(project_root=tmp_path)
    assert any(
        f.severity == Severity.CRITICAL and "manual_blocks" in f.snippet
        for f in findings
    )


def test_missing_required_field_reports_warning(tmp_path: Path):
    _make_change(tmp_path, "foo", "phase: v2.1\n")
    findings = run_check(project_root=tmp_path)
    assert any(f.severity == Severity.WARNING for f in findings)


def test_no_changes_dir_returns_no_findings(tmp_path: Path):
    findings = run_check(project_root=tmp_path)
    assert findings == []