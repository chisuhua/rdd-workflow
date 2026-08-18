"""Tests for tasks_checkbox_check (cat-5) — degraded path is the critical case."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from checks.tasks_checkbox_check import run as run_check  # noqa: E402


def _make_change_with_tasks(tmp_path: Path, name: str, content: str) -> None:
    change = tmp_path / "openspec" / "changes" / name
    change.mkdir(parents=True)
    (change / "tasks.md").write_text(content)


def test_well_formed_tasks_returns_no_findings(tmp_path: Path):
    _make_change_with_tasks(tmp_path, "foo", """\
## 1. Setup
- [x] 1.1 do thing one
- [x] 1.2 do thing two
""")
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_incomplete_tasks_reports_warning(tmp_path: Path):
    _make_change_with_tasks(tmp_path, "foo", """\
## 1. Setup
- [ ] 1.1 do thing one
- [x] 1.2 do thing two
""")
    findings = run_check(project_root=tmp_path)
    assert any(
        f.severity == Severity.WARNING and "tasks 1/2" in f.snippet
        for f in findings
    )


def test_missing_tasks_file_reports_warning(tmp_path: Path):
    (tmp_path / "openspec" / "changes" / "foo").mkdir(parents=True)
    # No tasks.md
    findings = run_check(project_root=tmp_path)
    assert any(
        f.severity == Severity.WARNING and "missing" in f.snippet
        for f in findings
    )


def test_zero_checkboxes_skips(tmp_path: Path):
    """0 checkboxes = skip (handled by archive_change check_tasks_completion)."""
    _make_change_with_tasks(tmp_path, "foo", "# Empty tasks\n\nNo items here.\n")
    findings = run_check(project_root=tmp_path)
    assert not any(
        "checkbox count = 0" in f.snippet for f in findings
    )


def test_zero_percent_completion_emits_info(tmp_path: Path):
    _make_change_with_tasks(tmp_path, "foo", """\
## 1. Setup
- [ ] 1.1 do thing one
- [ ] 1.2 do thing two
""")
    findings = run_check(project_root=tmp_path)
    info_findings = [f for f in findings if f.severity == Severity.INFO]
    assert any(
        "tasks 0/2" in f.snippet for f in info_findings
    )


def test_emit_info_when_openspec_cli_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Degraded path: openspec not on PATH → INFO finding, NOT exit-3."""
    _make_change_with_tasks(tmp_path, "foo", "- [x] 1.1 do thing\n")
    monkeypatch.setenv("PATH", "")
    findings = run_check(project_root=tmp_path)
    info_findings = [f for f in findings if f.severity == Severity.INFO]
    assert any(
        "openspec status unavailable" in f.snippet for f in info_findings
    )