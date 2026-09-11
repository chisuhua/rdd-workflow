"""Tests for doctor_main — single-process aggregator."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from doctor_main import aggregate_findings, _CHECKERS  # noqa: E402


_CATEGORY_NAMES = frozenset({
    "state", "plan-tdd", "roadmap-meta", "proposal-table",
    "proposal-section", "tasks-checkbox", "migration-residue",
    "orphan-gates", "roadmap-refs", "docs-consistency", "gitignore",
    "bypass-audit",
})


def test_category_names_constant_matches_disk():
    """Lock invariant: directory file count == wired category count.

    Per fix-update-doctor-main-category-count (Wave 1 P2): prevent future
    drift between source code and the _CATEGORY_NAMES set.
    """
    checks_dir = _SCRIPTS_DIR / "checks"
    files = [f for f in checks_dir.glob("*.py") if f.stem != "__init__"]
    assert len(_CATEGORY_NAMES) == len(files), (
        f"_CATEGORY_NAMES has {len(_CATEGORY_NAMES)} entries but {checks_dir} "
        f"has {len(files)} check files. Update _CATEGORY_NAMES."
    )


def test_aggregate_runs_all_12_categories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """aggregate_findings invokes all 12 checker modules and combines results.

    Per rdd-doctor-docs-consistency change (2026-08-27, 10th category),
    add-gitignore-hard-protection change (2026-09-10, 11th category),
    and bypass-audit-mechanism change (2026-09-11, 12th category).
    """
    monkeypatch.setenv("RDDF_PROJECT_ROOT", str(tmp_path))
    findings, categories_checked = aggregate_findings(category=None)
    assert set(categories_checked) == _CATEGORY_NAMES


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


def test_checkers_dict_has_12_entries():
    """Lock the public contract: exactly 12 categories wired (10 baseline + gitignore + bypass-audit).

    Baseline 10 (per rdd-doctor-docs-consistency 2026-08-27) + gitignore
    (per add-gitignore-hard-protection 2026-09-10) + bypass-audit
    (per bypass-audit-mechanism 2026-09-11).
    """
    assert len(_CHECKERS) == 12
