"""Unit tests for _lib.docs_consistency (6 drift checks).

Each test calls a single check function and asserts no CRITICAL/WARNING
issues remain on master (after sync-package-skills-to-disk +
sync-agents-md-five-stage + this change have fixed the documented drift).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add repo root to sys.path so `from _lib.X import Y` resolves
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _lib.docs_consistency import (  # noqa: E402
    check_adr_list_completeness,
    check_npm_test_caveat,
    check_role_frontmatter,
    check_skill_count,
    check_stage_count,
    check_version_consistency,
    run_all,
)


def test_skill_count_aligned():
    """package.json::skills[] == INSTALL.md table == disk */SKILL.md count."""
    issues = check_skill_count()
    assert issues == [], f"skill count drift: {issues}"


def test_stage_count_consistent():
    """Banner mentions of stage count are consistent (五阶段 / 5-stage)."""
    issues = check_stage_count()
    assert issues == [], f"stage count drift in banner: {issues}"


def test_no_npm_test_anti_pattern():
    """No docs claim 'npm test 不跑 Python' (v3.0+ auto-runs pytest)."""
    issues = check_npm_test_caveat()
    assert issues == [], f"npm test anti-pattern: {issues}"


def test_version_consistency():
    """package.json::version matches README/INSTALL banner versions."""
    issues = check_version_consistency()
    # INFO is acceptable (e.g. INSTALL.md banner has no version); CRITICAL/WARNING not
    blocking = [i for i in issues if i["severity"] in ("CRITICAL", "WARNING")]
    assert blocking == [], f"version drift: {blocking}"


def test_adr_list_completeness():
    """AGENTS.md ADR list references all real ADR files on disk."""
    issues = check_adr_list_completeness()
    assert issues == [], f"ADR list drift: {issues}"


def test_role_frontmatter_all_phase_skills():
    """5 phase skills (guide-arch/design/plan/ship/rdd-verifier) all have role:."""
    issues = check_role_frontmatter()
    assert issues == [], f"role: frontmatter drift: {issues}"


def test_run_all_aggregates():
    """run_all returns the union of all 6 checks."""
    issues = run_all()
    # Each issue must be a well-formed dict with required fields
    for issue in issues:
        assert "severity" in issue
        assert "name" in issue
        assert "detail" in issue
        assert "fix_command" in issue
        assert issue["severity"] in ("CRITICAL", "WARNING", "INFO")


def test_check_skill_count_disk_invariant():
    """Sub-skill disk count is exactly 27 (matches package.json + INSTALL.md)."""
    from _lib.docs_consistency import _count_disk_skill_md
    assert _count_disk_skill_md() == 27, (
        f"expected 27 SKILL.md on disk, got {_count_disk_skill_md()}"
    )
