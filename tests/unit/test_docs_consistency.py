"""Unit tests for _lib.docs_consistency (6 drift checks).

Each test calls a single check function and asserts no CRITICAL/WARNING
issues remain on master (after sync-package-skills-to-disk +
sync-agents-md-five-stage + this change have fixed the documented drift).
"""
from __future__ import annotations

import re
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
    check_schema_path_canonical,
    check_schema_readme_drift,
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


def test_adr_reverse_drift_no_false_positive():
    """AGENTS.md declares latest ADR == disk max → no reverse-drift issue.

    Regression guard: after B-1 sync (AGENTS.md claims ADR-0050 == disk ADR-0050),
    the new reverse-drift check must NOT fire.
    """
    from _lib import docs_consistency as dc

    issues = dc.check_adr_list_completeness()
    reverse = [i for i in issues if i["name"] == "adr-list-reverse-drift"]
    assert reverse == [], (
        f"unexpected reverse-drift when AGENTS.md is in sync: {reverse}"
    )


def test_adr_reverse_drift_detects_underclaim(monkeypatch):
    """AGENTS.md declares 最新编号落后于磁盘最大编号 → emit WARNING."""
    from _lib import docs_consistency as dc

    real_read_text = dc._read_text

    adr_dir = dc.REPO_ROOT / "docs" / "adr"
    nums = []
    for p in adr_dir.glob("ADR-*.md"):
        m = re.match(r"ADR-(\d{4})", p.stem)
        if m:
            nums.append(int(m.group(1)))
    disk_max = max(nums)
    stale_claim = disk_max - 8

    def fake_read(rel_path: str) -> str:
        if rel_path == "AGENTS.md":
            return (
                "fake preamble\n"
                f"- 当前最新编号: **ADR-{stale_claim:04d}** (v4 stage-merge Wave 3 hard removal)\n"
                "fake trailer\n"
            )
        return real_read_text(rel_path)

    monkeypatch.setattr(dc, "_read_text", fake_read)

    issues = dc.check_adr_list_completeness()
    reverse = [i for i in issues if i["name"] == "adr-list-reverse-drift"]

    assert len(reverse) == 1, f"expected exactly 1 reverse-drift issue, got: {issues}"
    issue = reverse[0]
    assert issue["severity"] == "WARNING"
    assert f"ADR-{disk_max:04d}" in issue["detail"]
    assert f"ADR-{stale_claim:04d}" in issue["detail"]
    assert "fix_command" in issue
    assert "AGENTS.md" in issue["fix_command"]


def test_schema_readme_drift_detects_missing_schema(tmp_path, monkeypatch):
    """docs/schemas/README.md references a _lib/schemas/ file that does NOT exist on disk → WARNING."""
    from _lib import docs_consistency as dc

    fake_schema_dir = tmp_path / "_lib" / "schemas"
    fake_schema_dir.mkdir(parents=True)
    (fake_schema_dir / "real_one_schema.json").write_text("{}")
    (fake_schema_dir / "real_two_schema.json").write_text("{}")

    fake_readme = (
        "# Index\n\n"
        "| Schema | Path |\n"
        "|---|---|\n"
        '| [ghost](_lib/schemas/ghost_schema.json) | _lib/schemas/ghost_schema.json |\n'
        '| [real_one](_lib/schemas/real_one_schema.json) | _lib/schemas/real_one_schema.json |\n'
    )

    monkeypatch.setattr(dc, "REPO_ROOT", tmp_path)

    (tmp_path / "docs" / "schemas").mkdir(parents=True)
    (tmp_path / "docs" / "schemas" / "README.md").write_text(fake_readme)

    issues = dc.check_schema_readme_drift()
    drift = [i for i in issues if i["name"] == "schema-readme-drift"]
    assert len(drift) == 1
    issue = drift[0]
    assert issue["severity"] == "WARNING"
    assert "ghost_schema.json" in issue["detail"]
    assert "real_two_schema.json" in issue["detail"]


def test_schema_readme_drift_no_false_positive():
    """Current docs/schemas/README.md in sync with _lib/schemas/ → no drift."""
    from _lib import docs_consistency as dc

    issues = dc.check_schema_readme_drift()
    drift = [i for i in issues if i["name"] == "schema-readme-drift"]
    assert drift == [], f"unexpected schema-readme drift: {drift}"


def test_schema_path_canonical_violation(tmp_path, monkeypatch):
    """skills/_lib/schemas/ outside a shim-context parenthetical → WARNING."""
    from _lib import docs_consistency as dc

    fake_agents = (
        "## Heading\n"
        "打开 schemas/foo.json 在 skills/_lib/schemas/  # violation\n"
        "(skills/_lib/schemas/ 是向后兼容 shim, 优先用 _lib/schemas/)  # allowed\n"
    )

    monkeypatch.setattr(dc, "REPO_ROOT", tmp_path)
    (tmp_path / "AGENTS.md").write_text(fake_agents)

    issues = dc.check_schema_path_canonical()
    violations = [i for i in issues if i["name"] == "schema-path-canonical-violation"]

    assert len(violations) == 1, f"expected 1 violation, got: {issues}"
    issue = violations[0]
    assert issue["severity"] == "WARNING"
    assert "skills/_lib/schemas/" in issue["detail"]
    assert "_lib/schemas/" in issue["fix_command"]


def test_schema_path_canonical_no_false_positive():
    """Current AGENTS.md / README.md only mention skills/_lib/schemas/ as shim context."""
    from _lib import docs_consistency as dc

    issues = dc.check_schema_path_canonical()
    violations = [i for i in issues if i["name"] == "schema-path-canonical-violation"]
    assert violations == [], f"unexpected path-canonical violations: {violations}"


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
    """Sub-skill disk count is exactly 26 (matches package.json + INSTALL.md post-Wave 3)."""
    from _lib.docs_consistency import _count_disk_skill_md
    assert _count_disk_skill_md() == 26, (
        f"expected 26 SKILL.md on disk, got {_count_disk_skill_md()}"
    )
