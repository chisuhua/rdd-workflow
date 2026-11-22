"""Cross-doc / cross-spec contract tests for sync-workflow-contracts.

锁定 v3.0 rdd-workflow 仓库内多 surface 一致性：
- openspec/specs/general/spec.md
- USAGE.md / AGENTS.md / INSTALL.md / package.json
- docs/adr/README.md
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text()


# `openspec/` is gitignored in this repo (change + spec artifacts are local, see
# .gitignore) ⇒ a fresh checkout — CI in particular — has no
# openspec/specs/general/spec.md. The contract is still worth checking where the
# file exists (a maintainer's worktree), so these tests SKIP instead of failing
# on a file the repo deliberately does not carry.
_GENERAL_SPEC = REPO_ROOT / "openspec" / "specs" / "general" / "spec.md"
requires_general_spec = pytest.mark.skipif(
    not _GENERAL_SPEC.is_file(),
    reason="openspec/ is gitignored (local-only artifacts): no specs/general/spec.md here",
)


@requires_general_spec
def test_general_spec_phase_count_matches_usaged() -> None:
    spec = _read("openspec/specs/general/spec.md")
    assert "7 numbered subphases" in spec or "7 编号子阶段" in spec
    assert "5 阶段 + 1 退出" not in spec, (
        "general/spec.md still references the v1.x '5 阶段 + 1 退出' ship-side"
    )


@requires_general_spec
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


@requires_general_spec
def test_general_spec_names_current_improvement_consumers() -> None:
    """The consumer list in general/spec.md must name **current** skills.

    Retired stage names are guarded by the spec-residue scanner
    (skills/rdd-doctor/scripts/spec_residue_scan.py); this test pins the
    positive side so the list cannot be emptied out either.
    """
    spec = _read("openspec/specs/general/spec.md")
    for name in ("rdd-planner", "rdd-builder", "propose", "add-improve"):
        assert name in spec, f"general/spec.md missing current consumer '{name}'"


def _improvement_consumer_skills(doc: str) -> list[str]:
    """Parse the first column of the `## Consumers` table.

    Returns the skill names listed there (backticks and a trailing `.md`
    suffix are stripped so the result can be compared against
    `skills/<name>/SKILL.md`).
    """
    names: list[str] = []
    in_section = False
    for raw in doc.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            in_section = line.strip("# ").strip().lower() == "consumers"
            continue
        if not in_section or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        first = cells[0].strip("`").removesuffix(".md")
        if not first or set(first) <= set("-—"):
            continue
        if first.lower() == "skill":
            continue
        names.append(first)
    return names


def test_improvement_suggestions_format_consumer_list_current() -> None:
    """docs/improvement-suggestions-format.md consumer list = existing skills only."""
    doc = _read("docs/improvement-suggestions-format.md")
    names = _improvement_consumer_skills(doc)
    assert names, "no consumer table parsed from the '## Consumers' section"
    for name in names:
        assert (REPO_ROOT / "skills" / name / "SKILL.md").is_file(), (
            f"consumer '{name}' has no skills/{name}/SKILL.md on disk"
        )
    for expected in ("rdd-planner", "rdd-builder", "propose", "add-improve"):
        assert expected in names, f"consumer list missing '{expected}' (got {names})"


def test_improvement_suggestions_format_no_retired_stage_names() -> None:
    """The format doc must not reference retired stage names any more."""
    doc = _read("docs/improvement-suggestions-format.md")
    for retired in ("guide-spec", "guide-arch", "guide-plan", "guide-ship", "guide-design"):
        assert retired not in doc, f"doc still references retired stage '{retired}'"


def test_superseded_adr_0001_marked_in_index() -> None:
    """A superseded ADR must be marked as such in the ADR and in the index."""
    adr = _read("docs/adr/ADR-0001-propose-plan-execute-state-machine.md")
    assert "已替代为 ADR-0002 + ADR-0003" in adr
    readme = _read("docs/adr/README.md")
    assert "已替代为 ADR-0002 + ADR-0003" in readme


def _skills_markdown_files() -> list[Path]:
    return sorted((REPO_ROOT / "skills").rglob("*.md"))


def test_skill_instruction_files_have_no_hardcoded_project_path() -> None:
    """The instruction surface (skills/**/*.md) must not name a concrete project.

    Generic placeholders (``/path/to/<repo>``, ``<project-root>``,
    ``~/.config/opencode``, ``${PROJECT_ROOT}``) are allowed.
    """
    forbidden = (
        re.compile(r"/path/to/CppHDL"),
        re.compile(r"/workspace/project/"),
        re.compile(r"/home/[^/\s]+/\.config/"),
    )
    for path in _skills_markdown_files():
        text = path.read_text()
        for pattern in forbidden:
            assert not pattern.search(text), (
                f"{path.relative_to(REPO_ROOT)} hardcodes a concrete path ({pattern.pattern})"
            )


def test_docs_do_not_claim_npm_test_skips_python() -> None:
    """`npm test` runs bats AND pytest (v3.0+) — the docs must not claim otherwise."""
    stale_phrases = (
        "不跑 Python",
        "不会跑 pytest",
        "不会自动跑",
        "仅覆盖 shell 测试",
        "只跑 bats",
        "不会**捕获 Python 测试失败",
    )
    for rel in ("USAGE.md", "AGENTS.md"):
        text = _read(rel)
        for lineno, line in enumerate(text.splitlines(), 1):
            if "npm test" not in line:
                continue
            for phrase in stale_phrases:
                assert phrase not in line, (
                    f"{rel}:{lineno} claims npm test skips Python ({phrase!r}): {line.strip()}"
                )
        assert "bats + pytest" in text, f"{rel} does not state that npm test runs pytest"


def test_tests_readme_layout_lists_every_top_level_entry() -> None:
    """tests/README.md Layout must list every top-level dir + the root test files."""
    readme = _read("tests/README.md")
    layout = readme.split("## Layout", 1)[1].split("```", 2)[1]
    for name in sorted(
        p.name + ("/" if p.is_dir() else "")
        for p in (REPO_ROOT / "tests").iterdir()
        if p.name != "__pycache__"
    ):
        assert name in layout, f"tests/README.md Layout does not list '{name}'"
    assert "deps-subagent.bash" in layout


def test_skill_count_in_narrative_docs_matches_disk() -> None:
    """Sub-skill counts in README.md / AGENTS.md must equal the canonical disk count."""
    disk = _count_skill_files()
    for rel in ("README.md", "AGENTS.md"):
        text = _read(rel)
        counts = [int(n) for n in re.findall(r"(\d+)\s*个子技能", text)]
        assert counts, f"{rel} states no sub-skill count"
        for n in counts:
            assert n == disk, f"{rel} claims {n} sub-skills, disk has {disk}"


def _count_skill_files(include_top_level: bool = False) -> int:
    """Count canonical sub-skill SKILL.md files.

    Args:
        include_top_level: If True, also count `skills/INSTALL.md`
            (top-level installer). Default False to match INSTALL.md
            ("N 个子技能") and package.json (`skills: [...N entries]`),
            both of which exclude INSTALL.

    Per fix-disk-count-semantic-conflict: the parameter exists so future
    tests can opt in to including INSTALL when verifying the
    installer-discovers-disks contract.

    Per Stage 3 ADR-0042: guide-arch is a deprecated shim forwarding to
    rdd-arch; excluded from canonical count.
    """
    canonical = []
    for skill_md in (REPO_ROOT / "skills").glob("*/SKILL.md"):
        text = skill_md.read_text()
        if not re.search(r"metadata:.*deprecated:", text, re.DOTALL):
            canonical.append(skill_md)
    total = len(canonical)
    if include_top_level:
        install = REPO_ROOT / "skills" / "INSTALL.md"
        if install.is_file():
            total += 1
    return total


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
    assert len(pkg["skills"]) == disk, (
        f"package.json declares {len(pkg['skills'])} skills, disk has {disk}"
    )


def test_install_sub_skill_table_count_matches_disk() -> None:
    disk = _count_skill_files()
    inst = _read("skills/INSTALL.md")
    names: set[str] = set()
    in_sub_skill_table = False
    for raw_line in inst.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            in_sub_skill_table = False
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        if first.startswith("技能名称"):
            in_sub_skill_table = True
            continue
        if not in_sub_skill_table:
            continue
        if set(first) <= set("-—"):
            continue
        cleaned = first.strip("`").strip()
        if cleaned:
            names.add(cleaned)
    assert len(names) == disk, (
        f"INSTALL.md sub-skill table rows={len(names)}, disk has {disk}; rows={sorted(names)}"
    )


@requires_general_spec
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

# ---------------------------------------------------------------------------
# Tests for fix-disk-count-semantic-conflict (include_top_level param)
# ---------------------------------------------------------------------------

def test_count_skill_files_default_excludes_install() -> None:
    """默认行为: 不含 INSTALL.md (匹配 package.json 和 bats 语义).

    Per Stage 3 ADR-0042: excludes deprecated shims (e.g. guide-arch)
    forwarding to canonical skills (e.g. rdd-arch).
    """
    disk = _count_skill_files()
    canonical = [
        p for p in (REPO_ROOT / "skills").glob("*/SKILL.md")
        if not re.search(r"metadata:.*deprecated:", p.read_text(), re.DOTALL)
    ]
    assert disk == len(canonical), (
        f"_count_skill_files()={disk} != canonical {len(canonical)}"
    )
    assert (REPO_ROOT / "skills" / "INSTALL.md").is_file()
    assert disk != _count_skill_files(include_top_level=True)


def test_count_skill_files_include_top_level_counts_install() -> None:
    """include_top_level=True 时, INSTALL.md 也被计入 (供 installer 验证)."""
    sub_count = _count_skill_files()
    with_install = _count_skill_files(include_top_level=True)
    assert with_install == sub_count + 1


def test_disk_count_matches_package_json() -> None:
    """Per AC: package.json::skills[] 与 disk count 一致 (不含 INSTALL)."""
    import json
    pkg = json.loads((REPO_ROOT / "package.json").read_text())
    declared = pkg.get("skills", [])
    disk = _count_skill_files()
    assert len(declared) == disk, (
        f"package.json has {len(declared)} entries, disk has {disk}"
    )


# ---------------------------------------------------------------------------
# fix-doc-truth-sync-false-assertions — 组 C 守卫（4 个）
#
# 背景（上一批教训）：判据 surface 必须覆盖同类文本。上一批修了
# `general/spec.md` + 7 份文档，却漏了 `doc-truth-sync/spec.md` 本身 ⇒ 两个 spec
# 互相矛盾（一个说 npm test 跑 bats+pytest，另一个说只跑 bats）。
# 本组守卫把「同类文本」全部纳入射程。
# ---------------------------------------------------------------------------

_DOC_TRUTH_SPEC = REPO_ROOT / "openspec" / "specs" / "doc-truth-sync" / "spec.md"
requires_doc_truth_spec = pytest.mark.skipif(
    not _DOC_TRUTH_SPEC.is_file(),
    reason="openspec/ is gitignored (local-only artifacts): no specs/doc-truth-sync/spec.md here",
)

_MIGRATION_GUIDE = REPO_ROOT / "docs" / "migration" / "v1-to-v2.md"


@requires_doc_truth_spec
def test_doc_truth_sync_spec_npm_test_assertion_matches_package_json() -> None:
    """`doc-truth-sync/spec.md` 的 D5 必须与 `package.json::scripts.test` 同向。

    实现侧（v3.0+）：`npm test` = `npm run test:bats && npm run test:python`
    ⇒ bats 与 pytest **都跑**。spec 不得再要求「只跑 bats」。
    """
    pkg = json.loads(_read("package.json"))
    script = pkg["scripts"]["test"]
    assert "test:bats" in script and "test:python" in script, (
        f"package.json::scripts.test no longer runs both suites: {script!r}"
    )

    spec = _DOC_TRUTH_SPEC.read_text()
    forbidden = (
        "exactly `bats tests/`",
        "MUST only run bats",
        "npm test MUST only run bats",
        "to be a separate, explicit invocation",
        "no longer\n  contains exactly",
    )
    for phrase in forbidden:
        assert phrase not in spec, (
            f"doc-truth-sync/spec.md still asserts npm test runs bats only ({phrase!r})"
        )
    assert "npm test` composition drift" in spec, (
        "doc-truth-sync/spec.md lost the D5 drift-class bullet"
    )


def test_readme_skills_tree_entries_match_disk() -> None:
    """README.md 的 `skills/` 树必须与 disk 双向一致（禁 dangling + 禁遗漏）。

    条目抽取规则：只取 `skills/` 子树内形如 `├── X` / `└── X` 的条目。
    含 `<` `>` 的占位模式（如 `<skill>/scripts/`）不参与 dangling 判定。
    """
    readme = _read("README.md")
    lines = readme.splitlines()
    start = next(
        i for i, line in enumerate(lines) if line.rstrip().endswith("└── skills/")
    )
    entries: list[str] = []
    for line in lines[start:]:
        if line.strip().startswith("```"):
            break
        m = re.match(r"\s*[├└]── (.+?)(?:\s+#.*)?$", line)
        if not m:
            continue
        entry = m.group(1).strip()
        if entry.startswith("skills/") or entry.startswith("<"):
            continue
        entries.append(entry)

    assert entries, "README.md skills tree yielded no entries"
    for entry in entries:
        assert (REPO_ROOT / "skills" / entry).exists(), (
            f"README.md skills tree lists {entry!r}, which does not exist on disk"
        )

    on_disk = {p.parent.name for p in (REPO_ROOT / "skills").glob("*/SKILL.md")}
    listed = {e.replace("/SKILL.md", "") for e in entries if e.endswith("/SKILL.md")}
    missing = sorted(on_disk - listed)
    assert not missing, f"README.md skills tree omits on-disk skills: {missing}"


# 目录构成计数 / 测试规模计数 —— 会随每次新增文件漂移的硬编码数字。
# 豁免：skill 计数（已由 test_skill_count_in_narrative_docs_matches_disk 动态锁定）。
_COUNT_CLAIM = re.compile(
    r"(?<![\w.-])\d+(?:\s*(?:个|files|\.py|\.sh|schema|cases|scenarios|tests|用例|模块|条|主题文件"
    r"|CLI|subcommands?|子命令|commands?))"
    r"|\d+/\d+\s*pass"
)
_COUNT_CLAIM_EXEMPT = (
    "26 个子技能",   # skill 计数 —— 由既有动态守卫锁定
    "26 SKILL.md",   # 同上
)


def _auto_generated_lines(text: str) -> set[int]:
    """AGENTS.md 的 AUTO 段由 `rddf roadmap --update-agent-md` 生成 ⇒ 不可手改。"""
    out: set[int] = set()
    inside = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if "AUTO:" in line and "start" in line:
            inside = True
        if "AUTO:" in line and "end" in line:
            inside = False
            continue
        if inside:
            out.add(lineno)
    return out


def test_docs_do_not_hardcode_directory_composition_counts() -> None:
    """README.md / AGENTS.md 不得硬编码会随新增文件漂移的构成计数。

    判据来源：这些数字每次加文件/加测试都会失真（实测已修正 20+ 处），
    且没有任何守卫覆盖 ⇒ 按 truth-source hierarchy（L4 跟随 L2），文档里
    的计数快照属于被禁的漂移类。
    """
    for rel in ("README.md", "AGENTS.md"):
        text = _read(rel)
        auto = _auto_generated_lines(text) if rel == "AGENTS.md" else set()
        for lineno, line in enumerate(text.splitlines(), 1):
            if lineno in auto:
                continue
            for m in _COUNT_CLAIM.finditer(line):
                claim = m.group(0).strip()
                if any(ex in line for ex in _COUNT_CLAIM_EXEMPT):
                    continue
                assert not claim, (
                    f"{rel}:{lineno} hardcodes a drift-prone count ({claim!r}): "
                    f"{line.strip()[:120]}"
                )


# ---------------------------------------------------------------------------
# retire-placeholder-spec-requirements — placeholder Requirement 守卫
#
# `openspec archive` 写出的 capability spec 若只有自动生成的正文
# （"The system SHALL provide X functionality." + "WHEN user invokes the feature
# / THEN system implements X correctly"），它对任何实现都恒真 ⇒ 零契约，
# 却让 `openspec validate` 报 "spec is valid"，制造「已覆盖」的错觉。
#
# 判据实现放在**已跟踪**的 `skills/rdd-doctor/scripts/spec_residue_scan.py`
# （与残留扫描同处一个模块，为将来 `git.openspec_tracked=true` 时零改动），
# 本文件只做 pytest 包装。
# ---------------------------------------------------------------------------

_SPECS_DIR = REPO_ROOT / "openspec" / "specs"
requires_specs_dir = pytest.mark.skipif(
    not _SPECS_DIR.is_dir(),
    reason="openspec/ is gitignored (local-only artifacts): no openspec/specs/ here",
)


@requires_specs_dir
def test_no_spec_contains_placeholder_requirement_body() -> None:
    """`openspec/specs/**` 不得含自动生成的 placeholder Requirement 体。"""
    sys.path.insert(0, str(REPO_ROOT / "skills" / "rdd-doctor" / "scripts"))
    try:
        from spec_residue_scan import scan_placeholder_requirements
    finally:
        sys.path.pop(0)

    result = scan_placeholder_requirements(_SPECS_DIR)
    assert result.checked_anything, "no spec scanned — cannot claim clean"
    offenders = [f"{h.file}:{h.line} ({h.kind})" for h in result.hits]
    assert not offenders, (
        "placeholder Requirement bodies remain (zero-information contracts):\n  "
        + "\n  ".join(offenders)
    )


def test_migration_guide_fictional_cli_refs_carry_planned_marker() -> None:
    """迁移指南里每处虚构 CLI 引用必须带「规划中」标记。

    旧判据「零引用」与它自身的 AND 子句（「或明确的 planned for v2.1 标记」）
    矛盾 —— 实测 6 处引用全部是带标记的历史记录。
    """
    markers = ("规划中", "planned", "未实现")
    for lineno, line in enumerate(_MIGRATION_GUIDE.read_text().splitlines(), 1):
        if not re.search(r"rdd-workflow (migrate|sync|report)", line):
            continue
        assert any(m in line for m in markers), (
            f"docs/migration/v1-to-v2.md:{lineno} mentions a fictional CLI "
            f"without a planned marker: {line.strip()[:120]}"
        )
