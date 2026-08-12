"""Tests for doctor_main — single-process aggregator."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from doctor_main import aggregate_findings, _CHECKERS  # noqa: E402


def test_aggregate_runs_all_6_categories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """aggregate_findings invokes all 6 checker modules and combines results."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings, categories_checked = aggregate_findings(category=None)
    assert set(categories_checked) == {
        "state", "plan-tdd", "roadmap-meta", "proposal-table",
        "tasks-checkbox", "migration-residue",
    }


def test_aggregate_with_category_filter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings, categories_checked = aggregate_findings(category="state")
    assert categories_checked == ["state"]


def test_aggregate_handles_checker_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """If one checker raises, others still report."""
    import doctor_main as main_mod

    def broken_check(project_root):
        raise RuntimeError("simulated checker crash")

    monkeypatch.setattr(main_mod, "_CHECKERS", {
        "broken": broken_check,
        "ok": lambda p: [],
    })
    findings, categories_checked = aggregate_findings(category=None)
    assert isinstance(findings, list)
    assert any("simulated checker crash" in f.snippet for f in findings)


def test_aggregate_no_category_no_match_returns_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Unknown category name returns empty result (no side effects)."""
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings, categories_checked = aggregate_findings(category="does-not-exist")
    assert findings == []
    assert categories_checked == []


def test_checkers_dict_has_6_entries():
    """Lock the public contract: exactly 6 categories wired."""
    assert len(_CHECKERS) == 6