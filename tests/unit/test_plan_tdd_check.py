"""Tests for plan_tdd_check (cat-2)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from checks.plan_tdd_check import run as run_check  # noqa: E402


def _write_plan(tmp_path: Path, name: str, content: str) -> None:
    plans = tmp_path / ".rddf" / "plans"
    plans.mkdir(parents=True)
    (plans / f"{name}.md").write_text(content)


def test_complete_plan_no_findings(tmp_path: Path):
    _write_plan(tmp_path, "foo", """\
# Plan
## Task 1: Setup
- [ ] Step 1: Write the failing test
- [ ] Step 2: Run test to verify it fails
- [ ] Step 3: Write minimal implementation
- [ ] Step 4: Run test to verify it passes
- [ ] Step 5: Defer commit
""")
    findings = run_check(project_root=tmp_path)
    assert findings == []


def test_missing_step_reports_warning(tmp_path: Path):
    """Missing 'verify it fails' marker → WARNING (S3 root cause scenario)."""
    _write_plan(tmp_path, "foo", """\
# Plan
## Task 1: Setup
- [ ] Step 1: Write the failing test
- [ ] Step 2: skip verify fail
- [ ] Step 3: Write minimal implementation
- [ ] Step 4: Run test to verify it passes
- [ ] Step 5: Defer commit
""")
    findings = run_check(project_root=tmp_path)
    assert any(
        f.severity == Severity.WARNING and "missing TDD step markers" in f.snippet
        for f in findings
    )


def test_no_plans_dir_returns_no_findings(tmp_path: Path):
    findings = run_check(project_root=tmp_path)
    assert findings == []