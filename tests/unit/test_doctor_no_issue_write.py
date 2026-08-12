"""Boundary regression: rdd-doctor MUST NOT trigger the issue reporter.

Per ADR-0027 §1.0, rdd-doctor is a static scanner for project-level
config/schema issues. Its findings should be fixed in the third-party
project, NOT reported as rdd-workflow bugs. This test guards the
boundary so future doctor refactors don't accidentally wire it into
the reporter.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "_lib"))


def test_doctor_does_not_import_issue_reporter():
    """rdd-doctor's doctor module must not import issue_reporter / post_flow_analysis."""
    doctor_dir = _PROJECT_ROOT / "skills" / "rdd-doctor"
    if not doctor_dir.is_dir():
        pytest.skip("rdd-doctor not installed in this checkout")

    for py_file in doctor_dir.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="replace")
        assert "from issue_reporter" not in text, (
            f"{py_file} imports issue_reporter — violates ADR-0027 §1.0 boundary"
        )
        assert "from post_flow_analysis" not in text, (
            f"{py_file} imports post_flow_analysis — violates ADR-0027 §1.0 boundary"
        )
        assert "import issue_reporter" not in text, (
            f"{py_file} imports issue_reporter — violates ADR-0027 §1.0 boundary"
        )


def test_doctor_does_not_write_to_rddf_issues():
    """rdd-doctor's bash scripts must not write to .rddf/issues/."""
    doctor_dir = _PROJECT_ROOT / "skills" / "rdd-doctor"
    if not doctor_dir.is_dir():
        pytest.skip("rdd-doctor not installed in this checkout")

    for sh_file in doctor_dir.rglob("*.sh"):
        text = sh_file.read_text(encoding="utf-8", errors="replace")
        # Allow read-only references but block writes
        assert not re.search(r">\s*['\"]?\.rddf/issues", text), (
            f"{sh_file} writes to .rddf/issues/ — violates ADR-0027 §1.0 boundary"
        )
        assert "write_issue_file" not in text, (
            f"{sh_file} calls write_issue_file — violates ADR-0027 §1.0 boundary"
        )


def test_doctor_does_not_call_report_issue_cli():
    """rdd-doctor's bash scripts must not invoke `rddf report-issue`."""
    doctor_dir = _PROJECT_ROOT / "skills" / "rdd-doctor"
    if not doctor_dir.is_dir():
        pytest.skip("rdd-doctor not installed in this checkout")

    for sh_file in doctor_dir.rglob("*.sh"):
        text = sh_file.read_text(encoding="utf-8", errors="replace")
        assert "rddf report-issue" not in text, (
            f"{sh_file} invokes rddf report-issue — violates ADR-0027 §1.0 boundary"
        )
        assert "rddf issue submit" not in text, (
            f"{sh_file} invokes rddf issue submit — violates ADR-0027 §1.0 boundary"
        )


def test_issue_reporter_explicitly_documents_doctor_boundary():
    """`_lib/issue_reporter.py` docstring must call out the rdd-doctor boundary."""
    reporter_file = _PROJECT_ROOT / "_lib" / "issue_reporter.py"
    text = reporter_file.read_text(encoding="utf-8", errors="replace")
    # The docstring should mention the rdd-doctor boundary somewhere
    assert "rdd-doctor" in text or "doctor" in text, (
        "issue_reporter.py docstring does not document the rdd-doctor boundary"
    )
