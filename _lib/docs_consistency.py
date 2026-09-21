"""docs-consistency doctor category: 6 类文档与代码一致性校验.

Read-only checks (no LLM). Output joins existing rdd-doctor report
(CRITICAL / WARNING / INFO).

Public API:
- check_skill_count() -> list[dict]
- check_stage_count() -> list[dict]
- check_npm_test_caveat() -> list[dict]
- check_version_consistency() -> list[dict]
- check_adr_list_completeness() -> list[dict]
- check_role_frontmatter() -> list[dict]
- run_all() -> list[dict] (aggregator)

Each check returns a list of issue dicts:
  {"severity": "CRITICAL"|"WARNING"|"INFO",
   "name": "<check-name>-<scope>",
   "detail": "<human-readable description>",
   "fix_command": "<actionable hint>"}

If a check passes, returns an empty list.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_text(rel_path: str) -> str:
    """Read a text file relative to REPO_ROOT."""
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def _read_json(rel_path: str) -> dict:
    """Read a JSON file relative to REPO_ROOT."""
    return json.loads(_read_text(rel_path))


def _count_disk_skill_md() -> int:
    """Count canonical sub-skill SKILL.md files.

    Excludes top-level INSTALL.md and deprecated shims (skills with
    metadata.deprecated set). Per Stage 3 ADR-0042: guide-arch is a
    shim forwarding to rdd-arch; both files exist on disk but only
    rdd-arch counts as canonical.
    """
    canonical = []
    for skill_md in (REPO_ROOT / "skills").glob("*/SKILL.md"):
        text = skill_md.read_text(encoding="utf-8")
        if not re.search(r"metadata:.*deprecated:", text, re.DOTALL):
            canonical.append(skill_md)
    return len(canonical)


def check_skill_count() -> list[dict]:
    """package.json::skills[] == INSTALL.md table rows == disk */SKILL.md count.

    INSTALL is excluded from disk count (it's the top-level installer, not
    a sub-skill). Per fix-skill-count-and-table-schema (2026-08-25).
    """
    issues = []
    pkg = _read_json("package.json")
    declared = len(pkg.get("skills", []))

    disk = _count_disk_skill_md()

    if declared != disk:
        issues.append({
            "severity": "CRITICAL",
            "name": "skill-count-package-vs-disk",
            "detail": f"package.json skills[]={declared}, disk */SKILL.md={disk}",
            "fix_command": "see sync-package-skills-to-disk proposal",
        })

    # INSTALL.md sub-skill table check
    install = _read_text("skills/INSTALL.md")
    table_names = set()
    in_table = False
    for raw in install.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        if first.startswith("技能名称"):
            in_table = True
            continue
        if not in_table:
            continue
        if set(first) <= set("-—"):
            continue
        cleaned = first.strip("`").strip()
        if cleaned:
            table_names.add(cleaned)

    if len(table_names) != disk:
        issues.append({
            "severity": "CRITICAL",
            "name": "skill-count-install-vs-disk",
            "detail": f"INSTALL.md table rows={len(table_names)}, disk */SKILL.md={disk}",
            "fix_command": "sync INSTALL.md sub-skill table to match disk",
        })

    return issues


def check_stage_count() -> list[dict]:
    """Stage architecture mentions are consistent (4 阶段 / 4-stage as of v4.0).

    Only reports WARNING for stage count mentions in the document's
    "frontmatter banner" (first 10 lines) — inline / changelog mentions
    of historical stage counts (e.g. "v2.1 从三阶段扩展为四阶段") are
    legitimate historical context and excluded.
    """
    issues = []

    for doc in ("README.md", "USAGE.md", "AGENTS.md"):
        try:
            text = _read_text(doc)
        except FileNotFoundError:
            continue

        # Only inspect the first 10 lines (banner / frontmatter)
        banner = "\n".join(text.splitlines()[:10])

        anti_patterns = re.findall(r"[三五](?=\s*阶段)", banner)
        if anti_patterns:
            issues.append({
                "severity": "WARNING",
                "name": f"stage-count-{doc}",
                "detail": (
                    f"{doc} banner (first 10 lines) contains {len(anti_patterns)} "
                    f"outdated stage count mention(s): {[a + '阶段' for a in anti_patterns]}. "
                    f"v4.0+ is 四阶段架构 (rdd-arch → rdd-planner → rdd-builder → rdd-verifier)."
                ),
                "fix_command": (
                    f"update {doc} banner to reference 四阶段 / 4-stage architecture"
                ),
            })

    return issues


def check_npm_test_caveat() -> list[dict]:
    """Detect old `npm test 不跑 Python` anti-pattern in docs.

    Post v3.0+, `npm test` = `npm run test:bats && npm run test:python`,
    so docs claiming `npm test` only runs bats are stale.
    """
    issues = []
    anti = re.compile(
        r"npm\s+test\s*(?:只跑|不会|不跑|仅跑|跳过|不\s*执\s*行|skip).{0,30}Python",
        re.IGNORECASE,
    )

    for doc in (
        "README.md",
        "AGENTS.md",
        "USAGE.md",
        "skills/INSTALL.md",
        "CHANGELOG.md",
    ):
        try:
            text = _read_text(doc)
        except FileNotFoundError:
            continue

        matches = anti.findall(text)
        if matches:
            issues.append({
                "severity": "CRITICAL",
                "name": f"npm-test-anti-pattern-{doc}",
                "detail": (
                    f"v3.0+ npm test auto-runs pytest (via package.json::scripts), "
                    f"but {doc} has {len(matches)} outdated 'npm test 不跑 Python' "
                    f"mention(s). Users may skip Python validation."
                ),
                "fix_command": (
                    f"update {doc} to remove 'npm test 不跑 Python' caveat; "
                    f"npm test now runs pytest automatically."
                ),
            })

    return issues


def check_version_consistency() -> list[dict]:
    """package.json::version matches README/INSTALL banner versions.

    Only inspects the banner (first 10 lines) of README/INSTALL. Inline
    / changelog mentions of historical versions are legitimate context.
    """
    issues = []
    pkg_version = _read_json("package.json").get("version", "")

    if not pkg_version:
        return [{
            "severity": "CRITICAL",
            "name": "version-missing-package-json",
            "detail": "package.json missing 'version' field",
            "fix_command": "add 'version' field to package.json",
        }]

    pkg_v_normalized = pkg_version.lstrip("v")

    for doc in ("README.md", "skills/INSTALL.md"):
        try:
            text = _read_text(doc)
        except FileNotFoundError:
            continue

        banner = "\n".join(text.splitlines()[:10])
        # Extract version mentions in the banner
        versions = re.findall(r"v(\d+\.\d+(?:\.\d+)?)", banner)
        if not versions:
            # No version in banner — this is itself a drift
            issues.append({
                "severity": "INFO",
                "name": f"version-banner-missing-{doc}",
                "detail": (
                    f"{doc} banner has no version mention. "
                    f"package.json version={pkg_version}."
                ),
                "fix_command": (
                    f"add version banner to {doc} (e.g. '> v{pkg_version}')"
                ),
            })
            continue

        if pkg_v_normalized not in versions and not any(
            v.startswith(pkg_v_normalized.split(".")[0] + ".")
            for v in versions
        ):
            issues.append({
                "severity": "WARNING",
                "name": f"version-drift-{doc}",
                "detail": (
                    f"package.json version={pkg_version}, but {doc} banner "
                    f"mentions {sorted(set(versions))[:3]} without {pkg_version}."
                ),
                "fix_command": (
                    f"update {doc} banner to reference {pkg_version}"
                ),
            })

    return issues


def check_adr_list_completeness() -> list[dict]:
    """AGENTS.md line 148 ADR list covers all real ADR-NNNN on disk.

    Reports WARNING for any ADR referenced in AGENTS.md but missing on
    disk (stale references). Also detects reverse drift: when the disk
    has a higher ADR number than AGENTS.md declares as "当前最新编号"
    on L291 (the underclaim case).
    """
    issues = []
    try:
        agents = _read_text("AGENTS.md")
    except FileNotFoundError:
        return []

    referenced = set(re.findall(r"ADR-(\d{4})", agents))

    adr_dir = REPO_ROOT / "docs" / "adr"
    if not adr_dir.exists():
        return []

    real = set()
    for p in adr_dir.glob("ADR-*.md"):
        m = re.match(r"ADR-(\d{4})", p.stem)
        if m:
            real.add(m.group(1))

    # AGENTS.md referenced but disk missing → stale reference
    stale = {f"ADR-{n}" for n in referenced if n not in real}
    if stale:
        issues.append({
            "severity": "WARNING",
            "name": "adr-list-stale-references",
            "detail": (
                f"AGENTS.md references {sorted(stale)} but no such file exists "
                f"in docs/adr/. These are stale references."
            ),
            "fix_command": (
                "remove stale ADR references from AGENTS.md, or create "
                "the missing ADR file"
            ),
        })

    # Reverse drift: disk max > AGENTS.md L291 "当前最新编号" claim
    # Only fire when AGENTS.md makes an explicit claim — silent skip otherwise.
    # Reverse drift: disk max > AGENTS.md L291 claim
    if real:
        max_real = max(int(n) for n in real)
        m = re.search(r"当前最新编号[:：]\s*\*\*?ADR-(\d{4})", agents)
        if m:
            claimed_max = int(m.group(1))
            if max_real > claimed_max:
                issues.append({
                    "severity": "WARNING",
                    "name": "adr-list-reverse-drift",
                    "detail": (
                        f"docs/adr/ has ADR-{max_real:04d} on disk but AGENTS.md "
                        f"declares 当前最新编号: ADR-{claimed_max:04d}. "
                        f"Update AGENTS.md L291 (and L148 ADR 范围段) "
                        f"to reflect ADR-{max_real:04d}."
                    ),
                    "fix_command": (
                        f"edit AGENTS.md L291 to '当前最新编号: "
                        f"**ADR-{max_real:04d}** (...); docs/adr/ 取最大值' "
                        f"and bump the L148 range to ~{max_real:04d}"
                    ),
                })

    return issues


def check_schema_readme_drift() -> list[dict]:
    """docs/schemas/README.md lists every _lib/schemas/*.json (and only those).

    Two-way drift detection:
      - README references a _lib/schemas/.json not on disk (ghost reference)
      - disk has a _lib/schemas/.json not referenced in README (missing entry)
    Either condition emits WARNING. The README is treated as a curated view;
    drift detection runs without modifying it (per Oracle advice: curatorship
    is human, drift is automated).
    """
    issues: list[dict] = []

    readme_rel = "docs/schemas/README.md"
    schema_dir = REPO_ROOT / "_lib" / "schemas"

    try:
        readme = _read_text(readme_rel)
    except FileNotFoundError:
        return []

    if not schema_dir.exists():
        return []

    referenced: set[str] = set(re.findall(r"_lib/schemas/([a-z0-9_]+\.json)", readme))
    on_disk: set[str] = {p.name for p in schema_dir.glob("*.json")}

    missing_in_disk = referenced - on_disk
    missing_in_readme = on_disk - referenced

    if missing_in_disk or missing_in_readme:
        parts: list[str] = []
        if missing_in_disk:
            parts.append(
                f"README references {len(missing_in_disk)} schema file(s) not on disk: "
                f"{sorted(missing_in_disk)}"
            )
        if missing_in_readme:
            parts.append(
                f"disk has {len(missing_in_readme)} schema file(s) not listed in README: "
                f"{sorted(missing_in_readme)}"
            )
        issues.append({
            "severity": "WARNING",
            "name": "schema-readme-drift",
            "detail": "docs/schemas/README.md is out of sync with _lib/schemas/. " + " ".join(parts),
            "fix_command": (
                "either delete the ghost references from README, or add a row for "
                "each missing schema (curated additions stay human-driven)"
            ),
        })

    return issues


def check_schema_path_canonical() -> list[dict]:
    """AGENTS.md / README.md reference schema paths as `_lib/schemas/` (canonical).

    The string `skills/_lib/schemas/` is allowed ONLY when it appears in a shim
    explanation (e.g. parenthetical "(skills/_lib/schemas/ 为向后兼容 shim)").
    Otherwise it is a stale reference (the canonical path is `_lib/schemas/`
    post P1-1b flatten layout, 2026-08-25).
    """
    SHIM_TOKENS = ("shim", "兼容", "向后兼容", "backward")
    targets = ("AGENTS.md", "README.md")

    violations: list[tuple[str, int, str]] = []
    for rel in targets:
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            for m in re.finditer(r"skills/_lib/schemas/", line):
                start = max(0, m.start() - 40)
                end = min(len(line), m.end() + 40)
                context = line[start:end].lower()
                prev = lines[i - 1] if i > 0 else ""
                prev_context = prev.lower()
                combined = context + " " + prev_context
                if any(tok in combined for tok in SHIM_TOKENS):
                    continue
                violations.append((rel, i + 1, line.strip()))

    if not violations:
        return []

    detail_lines = [
        f"{rel}:{lineno}: {snippet}" for rel, lineno, snippet in violations[:5]
    ]
    if len(violations) > 5:
        detail_lines.append(f"... and {len(violations) - 5} more")
    return [{
        "severity": "WARNING",
        "name": "schema-path-canonical-violation",
        "detail": (
            "Use the canonical schema path `_lib/schemas/` instead of "
            "`skills/_lib/schemas/`. Allowed only inside shim-compat "
            "parentheticals. Found " + str(len(violations)) + " stale reference(s):\n"
            + "\n".join(detail_lines)
        ),
        "fix_command": (
            "replace `skills/_lib/schemas/` with `_lib/schemas/` in the listed "
            "lines; or wrap the mention in parentheses with a shim note "
            "(e.g. '`skills/_lib/schemas/` 为向后兼容 shim')"
        ),
    }]


def check_role_frontmatter() -> list[dict]:
    """All 5 phase skills have role: frontmatter (per ADR-0028 + ADR-0034)."""
    issues = []
    phase_skills = (
        "rdd-arch",
        "rdd-planner",
        "rdd-builder",
        "rdd-verifier",
    )

    missing = []
    for skill in phase_skills:
        skill_md = REPO_ROOT / "skills" / skill / "SKILL.md"
        if not skill_md.exists():
            missing.append(f"{skill} (no SKILL.md)")
            continue
        text = skill_md.read_text(encoding="utf-8")
        if not re.search(r"^role:", text, re.MULTILINE):
            missing.append(skill)

    if missing:
        issues.append({
            "severity": "WARNING",
            "name": "role-frontmatter-missing",
            "detail": (
                f"5 phase skills should have role: frontmatter per ADR-0028 + "
                f"ADR-0034 §10. Missing: {missing}"
            ),
            "fix_command": (
                "add role: frontmatter (title / perspective / boundaries) "
                "to the listed SKILL.md files"
            ),
        })

    return issues


def check_skill_external_docs_refs() -> list[dict]:
    """Check that all skills/*/SKILL.md have no external docs/ references.

    Scans for ``../docs/`` and ``../../docs/`` patterns that would 404
    after ``install.sh`` (which does not distribute the ``docs/``
    directory). CRITICAL if any are found.
    """
    issues: list[dict] = []
    for skill_md in sorted(REPO_ROOT.glob("skills/*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), 1):
            if "../docs/" in line or "../../docs/" in line:
                rel = skill_md.relative_to(REPO_ROOT)
                issues.append({
                    "severity": "CRITICAL",
                    "name": f"skill-ext-docs-ref",
                    "detail": (
                        f"{rel}:{lineno} 包含外部 docs/ 引用: {line.strip()[:80]}"
                    ),
                    "fix_command": (
                        "重写该 SKILL.md 段落为自包含版本，移除对 docs/ 目录的相对引用"
                    ),
                })
    return issues


def run_all() -> list[dict]:
    """Aggregate all 9 docs-consistency checks."""
    return (
        check_skill_count()
        + check_stage_count()
        + check_npm_test_caveat()
        + check_version_consistency()
        + check_adr_list_completeness()
        + check_schema_readme_drift()
        + check_schema_path_canonical()
        + check_role_frontmatter()
        + check_skill_external_docs_refs()
    )
