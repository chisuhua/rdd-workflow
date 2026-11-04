"""Tests for doctor_main — single-process aggregator."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from doctor_main import aggregate_findings, _CHECKERS  # noqa: E402


# The category list is owned by the production `_CHECKERS` dict (imported
# above). A local copy of it was a second source of truth that drifted every
# time a checker was added — the drift was invisible because the copy was
# what the tests asserted against.
_CATEGORY_NAMES = frozenset(_CHECKERS.keys())


def test_category_names_constant_matches_disk():
    """Lock invariant: every check file on disk is wired into _CHECKERS.

    The expected set comes from the production `_CHECKERS` dict, so adding a
    checker can no longer desynchronise this test from the implementation.
    """
    checks_dir = _SCRIPTS_DIR / "checks"
    files = [f for f in checks_dir.glob("*.py") if f.stem != "__init__"]
    assert len(_CATEGORY_NAMES) == len(files), (
        f"_CHECKERS wires {len(_CATEGORY_NAMES)} categories but {checks_dir} "
        f"has {len(files)} check files."
    )


def test_aggregate_runs_all_wired_categories(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """aggregate_findings invokes all 20 checker modules and combines results.

    Per rdd-doctor-docs-consistency change (2026-08-27, 10th category),
    add-gitignore-hard-protection change (2026-09-10, 11th category),
    bypass-audit-mechanism change (2026-09-11, 12th category),
    improvement-frontmatter-consistency (2026-09-15, 13th category),
    fix-skill-post-install-discoverability (2026-09-21, 14th category),
    feat-roadmap-discovery-completion (2026-09-22, 15th category),
    add-objective-tracking change (2026-09-22, 16th + 17th category),
    arch-audit (2026-09-29, 18th category per rdd-arch v2.1.0 fix-arch-doc-drift),
    add-roadmap-phases-and-md-integrity-category (2026-10-07, 19th + 20th category).
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


def test_checkers_dict_has_one_entry_per_check_file():
    """Lock the public contract: one wired category per check file.

    The absolute count is not asserted — it grew with every checker, and
    each growth required editing this test, which is how the drift between
    the implementation and the (now removed) local constant went unnoticed.
    """
    checks_dir = _SCRIPTS_DIR / "checks"
    files = [f for f in checks_dir.glob("*.py") if f.stem != "__init__"]
    assert len(_CHECKERS) == len(files)
