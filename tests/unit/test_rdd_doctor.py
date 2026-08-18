"""Tests for rdd-doctor --check orphan-gates (fix-orphan-hub-gates-wiring).

Orphan gate = a gate function defined in design_done_gate.py that is never
referenced by check_design_done_gate() in skills/guide-design/SKILL.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402


def _make_project(tmp_path: Path, skill_md_calls: list[str]) -> Path:
    """Build a minimal fake project with a gate module + SKILL.md."""
    scripts = tmp_path / "skills" / "guide-design" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "design_done_gate.py").write_text(
        "def check_hub_pending():\n    return False\n\n"
        "def check_cross_repo_approvals():\n    return False\n"
    )
    body = "check_design_done_gate() {\n"
    for name in skill_md_calls:
        body += f"  {name}\n"
    body += "}\n"
    (tmp_path / "skills" / "guide-design" / "SKILL.md").write_text(body)
    return tmp_path


def test_orphan_gates_all_wired_no_findings(tmp_path: Path):
    from checks import orphan_gates_check

    root = _make_project(tmp_path, ["check_hub_pending", "check_cross_repo_approvals"])
    findings = orphan_gates_check.run(project_root=root)
    assert findings == []


def test_orphan_gates_detects_unwired_function_critical(tmp_path: Path):
    from checks import orphan_gates_check

    root = _make_project(tmp_path, ["check_hub_pending"])
    findings = orphan_gates_check.run(project_root=root)
    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert findings[0].category == "orphan-gates"
    assert "check_cross_repo_approvals" in findings[0].snippet


def test_orphan_gates_missing_files_no_crash(tmp_path: Path):
    """Missing gate module or SKILL.md → no findings, no exception."""
    from checks import orphan_gates_check

    assert orphan_gates_check.run(project_root=tmp_path) == []


def test_doctor_main_check_flag_selects_orphan_gates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`main(["--check", "orphan-gates"])` runs only the orphan-gates checker."""
    import doctor_main as main_mod

    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    rc = main_mod.main(["--check", "orphan-gates", "--quiet"])
    assert rc == 0


def test_orphan_gates_registered_in_checkers():
    from doctor_main import _CHECKERS

    assert "orphan-gates" in _CHECKERS
