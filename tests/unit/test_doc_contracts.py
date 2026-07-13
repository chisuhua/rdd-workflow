"""Cross-doc / cross-spec contract tests for sync-workflow-contracts.

锁定 v2.0.2 spec-workflow 仓库内多 surface 一致性：
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


def test_general_spec_no_guide_spec_reference() -> None:
    spec = _read("openspec/specs/general/spec.md")
    assert "guide-spec" not in spec, (
        "general/spec.md still references 'guide-spec' which was removed in v2.0"
    )


def test_general_spec_consumers_drop_guide_spec_add_arch_plan() -> None:
    spec = _read("openspec/specs/general/spec.md")
    assert "guide-arch" in spec
    assert "guide-plan" in spec


def test_install_description_skill_count_matches_disk() -> None:
    disk = len(list((REPO_ROOT / "skills").glob("*.md")))
    inst = _read("skills/INSTALL.md")
    m = re.search(r"全部\s*(\d+)\s*个子技能", inst)
    assert m is not None, "INSTALL.md description missing '全部 N 个子技能'"
    assert int(m.group(1)) == disk, (
        f"INSTALL.md claims {m.group(1)} skills, disk has {disk}"
    )


def test_package_json_skills_count_within_delta() -> None:
    pkg = json.loads(_read("package.json"))
    disk = len(list((REPO_ROOT / "skills").glob("*.md")))
    assert len(pkg["skills"]) <= disk + 2, (
        f"package.json declares {len(pkg['skills'])} skills, disk has {disk}"
    )


def test_state_file_paths_in_general_spec_use_canonical_paths() -> None:
    spec = _read("openspec/specs/general/spec.md")
    for tail in (".arch-handoff.json", ".plan-handoff.json",
                 ".deps-candidates.json", ".deps-output.md"):
        assert f".rddf/state/{tail}" in spec, f"missing '.rddf/state/{tail}'"
    assert ".rddf/state/deps-analysis.json" in spec
    assert ".sisyphus/plans" not in spec


def test_npm_test_trap_caveat_locked() -> None:
    pkg = json.loads(_read("package.json"))
    assert pkg["scripts"]["test"] == "bats tests/", (
        f"package.json::scripts.test is {pkg['scripts']['test']!r}"
    )


def test_adr_index_references_real_files() -> None:
    adr_dir = REPO_ROOT / "docs/adr"
    real = {p.name for p in adr_dir.glob("ADR-*.md")}
    readme = _read("docs/adr/README.md")
    referenced = set(re.findall(r"ADR-\d{4}-[\w-]+\.md", readme))
    missing = referenced - real
    assert not missing, f"docs/adr/README.md references missing: {sorted(missing)}"