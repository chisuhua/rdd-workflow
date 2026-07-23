"""Cross-doc / cross-spec contract tests for sync-workflow-contracts.

锁定 v3.0 rdd-workflow 仓库内多 surface 一致性：
- openspec/specs/general/spec.md
- USAGE.md / AGENTS.md / INSTALL.md / package.json
- docs/adr/README.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text()


def test_general_spec_phase_count_matches_usaged() -> None:
    spec = _read("openspec/specs/general/spec.md")
    assert "7 numbered subphases" in spec or "7 编号子阶段" in spec
    assert "5 阶段 + 1 退出" not in spec, (
        "general/spec.md still references the v1.x '5 阶段 + 1 退出' ship-side"
    )


def test_general_spec_no_active_guide_spec_reference() -> None:
    """guide-spec is allowed in legacy notes (e.g. 'removed in v2.0') but MUST NOT
    be prescribed as an active consumer in any Requirement body.
    """
    spec = _read("openspec/specs/general/spec.md")
    import re
    blocks = re.split(r"\n### Requirement: ", spec)
    for block in blocks[1:]:
        active_ref = re.search(
            r"(consumers?|skills?)\s+(include|are|should include|must include|:)\s+[^.\n]*guide-spec",
            block,
            re.IGNORECASE,
        )
        assert not active_ref, (
            f"general/spec.md prescribes 'guide-spec' as active in Requirement:\n{block[:200]}"
        )


def test_general_spec_consumers_drop_guide_spec_add_arch_plan() -> None:
    spec = _read("openspec/specs/general/spec.md")
    assert "guide-arch" in spec
    assert "guide-plan" in spec


def _count_skill_files() -> int:
    """Count skill .md files: top-level INSTALL.md + per-skill SKILL.md in subdirs."""
    top = list((REPO_ROOT / "skills").glob("*.md"))
    sub = list((REPO_ROOT / "skills").glob("*/SKILL.md"))
    return len(top) + len(sub)


def test_install_description_skill_count_matches_disk() -> None:
    disk = _count_skill_files()
    inst = _read("skills/INSTALL.md")
    m = re.search(r"全部\s*(\d+)\s*个子技能", inst)
    assert m is not None, "INSTALL.md description missing '全部 N 个子技能'"
    assert int(m.group(1)) == disk, (
        f"INSTALL.md claims {m.group(1)} skills, disk has {disk}"
    )


def test_package_json_skills_count_within_delta() -> None:
    pkg = json.loads(_read("package.json"))
    disk = _count_skill_files()
    assert len(pkg["skills"]) <= disk + 2, (
        f"package.json declares {len(pkg['skills'])} skills, disk has {disk}"
    )


def test_state_file_paths_in_general_spec_use_canonical_paths() -> None:
    spec = _read("openspec/specs/general/spec.md")
    for tail in (".arch-handoff.json", ".plan-handoff.json",
                 ".deps-candidates.json", ".deps-output.md"):
        assert f".rddf/state/{tail}" in spec, f"missing '.rddf/state/{tail}'"
    assert ".rddf/state/deps-analysis.json" in spec
    # .sisyphus/plans is allowed in legacy notes (e.g. "wrong directory") but MUST NOT
    # be prescribed as a canonical/active path in any Requirement body.
    import re
    blocks = re.split(r"\n### Requirement: ", spec)
    for block in blocks[1:]:
        active_ref = re.search(
            r"(path|directory|location)\s+(is|are|should be|must be|:)\s+[^.\n]*\.sisyphus/plans",
            block,
            re.IGNORECASE,
        )
        assert not active_ref, (
            f"general/spec.md prescribes '.sisyphus/plans' as active in Requirement:\n{block[:200]}"
        )


def test_npm_test_trap_caveat_locked() -> None:
    # v3.0: npm test now runs both bats and pytest.
    # v2.0.3: npm test now runs full recursive bats suite (--recursive flag).
    # The prior "bats tests/" only ran smoke.bats, which was the "trap" this
    # test was warning about. The fix was to use --recursive so developers
    # and CI both run the full integration test suite.
    pkg = json.loads(_read("package.json"))
    test_script = pkg["scripts"]["test"]
    
    # v3.0: Check that test:bats has --recursive
    bats_script = pkg["scripts"].get("test:bats", "")
    assert "--recursive" in bats_script, (
        f"package.json::scripts.test:bats must use --recursive to run all bats, "
        f"got: {bats_script!r}"
    )
    
    # v3.0: Check that test:python exists
    python_script = pkg["scripts"].get("test:python", "")
    assert "pytest" in python_script, (
        f"package.json::scripts.test:python must use pytest, "
        f"got: {python_script!r}"
    )
    
    # v3.0: Check that npm test runs both
    assert "test:bats" in test_script and "test:python" in test_script, (
        f"package.json::scripts.test must run both test:bats and test:python, "
        f"got: {test_script!r}"
    )


def test_adr_index_references_real_files() -> None:
    adr_dir = REPO_ROOT / "docs/adr"
    real = {p.name for p in adr_dir.glob("ADR-*.md")}
    readme = _read("docs/adr/README.md")
    referenced = set(re.findall(r"ADR-\d{4}-[\w-]+\.md", readme))
    missing = referenced - real
    assert not missing, f"docs/adr/README.md references missing: {sorted(missing)}"


def test_no_adr_0013_duplicate_on_disk() -> None:
    """After v2.0.2 renumber, only one ADR-0013 file should remain (extract-scan-state)."""
    adr_dir = REPO_ROOT / "docs/adr"
    adr_0013_files = list(adr_dir.glob("ADR-0013-*.md"))
    assert len(adr_0013_files) == 1, (
        f"Expected exactly 1 ADR-0013 file, found {len(adr_0013_files)}: "
        f"{[p.name for p in adr_0013_files]}"
    )
    assert adr_0013_files[0].name == "ADR-0013-extract-scan-state.md"
    # incremental-skeleton-planning should now live at ADR-0020
    assert (adr_dir / "ADR-0020-incremental-skeleton-planning.md").exists()