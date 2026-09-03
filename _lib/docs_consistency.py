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
    """Stage architecture mentions are consistent (5 阶段 / five-stage).

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

        # Disallowed (post v3.0+): 三阶段 / 四阶段 in the banner
        anti_patterns = re.findall(r"[三四](?=\s*阶段)", banner)
        if anti_patterns:
            issues.append({
                "severity": "WARNING",
                "name": f"stage-count-{doc}",
                "detail": (
                    f"{doc} banner (first 10 lines) contains {len(anti_patterns)} "
                    f"outdated stage count mention(s): {[a + '阶段' for a in anti_patterns]}. "
                    f"v3.0+ is 五阶段架构 (arch → design → plan → ship → verify)."
                ),
                "fix_command": f"update {doc} banner to reference 五阶段 / 5-stage architecture",
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
    disk (stale references).
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

    return issues


def check_role_frontmatter() -> list[dict]:
    """All 5 phase skills have role: frontmatter (per ADR-0028 + ADR-0034)."""
    issues = []
    phase_skills = (
        "rdd-arch",
        "guide-design",
        "guide-plan",
        "guide-ship",
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


def run_all() -> list[dict]:
    """Aggregate all 6 docs-consistency checks."""
    return (
        check_skill_count()
        + check_stage_count()
        + check_npm_test_caveat()
        + check_version_consistency()
        + check_adr_list_completeness()
        + check_role_frontmatter()
    )
