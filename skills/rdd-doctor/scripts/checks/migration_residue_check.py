"""Cat-6 — Detect stale migration references that ``rddf migrate-improvements --include-docs`` fixes.

This check is the read-only companion to ``_lib.cli.migrate_improvements_cmd``.
It detects the SAME patterns that the migrate command rewrites, so the doctor
report can:
1. Tell the user that stale references exist (visibility).
2. Show the exact command + flags needed to fix them (accuracy).

Two patterns are scanned (mirror of migrate_improvements_cmd.py regexes):
- ``](improvements/X)`` — legacy pre-migration markdown links
- ``](.rddf/.rddf/improvements/X)`` — double-prefix bug from an earlier
  migration that ran a naive s/pattern/replacement/

Only files in ``_DOC_LINK_FILES`` (AGENTS.md, README.md, USAGE.md,
docs/proposal-*-format.md) are scanned. Prose mentions of
``improvements/`` in backticks are intentionally NOT flagged — they are
descriptive and the command's regex skips them too (consistency).
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity


_LEGACY_LINK_REGEX = re.compile(r"\]\(improvements/([^)\s]+)\)")
_DOUBLE_PREFIX_REGEX = re.compile(r"\]\(\.rddf/\.rddf/improvements/([^)\s]+)\)")


_DOC_FILES = (
    "AGENTS.md",
    "README.md",
    "USAGE.md",
    "docs/proposal-suggestions-format.md",
    "docs/proposal-approved-format.md",
)


def _is_source_repo(project_root: Path) -> bool:
    """Detect the rdd-workflow source repo (needs --allow-source-repo)."""
    return (
        (project_root / "skills" / "INSTALL.md").is_file()
        and (project_root / ".rddf" / "improvements").is_dir()
    )


def _build_fix_hint(source_repo: bool) -> str:
    """Build the exact command preview shown to the user."""
    flags = ["--include-docs"]
    if source_repo:
        flags.append("--allow-source-repo")
    return "run: rddf migrate-improvements " + " ".join(flags)


def _scan_file(path: Path, fix_hint: str) -> Finding | None:
    """Return a Finding if the file has stale refs, else None."""
    try:
        text = path.read_text()
    except OSError:
        return None

    legacy_matches = _LEGACY_LINK_REGEX.findall(text)
    double_matches = _DOUBLE_PREFIX_REGEX.findall(text)

    if not legacy_matches and not double_matches:
        return None

    n_legacy = len(legacy_matches)
    n_double = len(double_matches)

    parts: list[str] = []
    if n_legacy:
        sample = ", ".join(f"improvements/{m}" for m in legacy_matches[:3])
        more = f" (+{n_legacy - 3} more)" if n_legacy > 3 else ""
        parts.append(f"{n_legacy} stale link{'s' if n_legacy != 1 else ''} "
                     f"[{sample}{more}] → ](.rddf/improvements/X)")
    if n_double:
        sample = ", ".join(f".rddf/.rddf/improvements/{m}" for m in double_matches[:3])
        more = f" (+{n_double - 3} more)" if n_double > 3 else ""
        parts.append(f"{n_double} double-prefix bug{'s' if n_double != 1 else ''} "
                     f"[{sample}{more}]")
    snippet = "; ".join(parts)

    return Finding(
        severity=Severity.WARNING,
        category="migration-residue",
        file=str(path),
        line=None,
        snippet=snippet,
        fix_hint=fix_hint,
    )


def run(project_root: Path | None = None) -> List[Finding]:
    """Run cat-6: scan doc files for stale migration references."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))

    fix_hint = _build_fix_hint(source_repo=_is_source_repo(project_root))

    findings: List[Finding] = []
    for relpath in _DOC_FILES:
        path = project_root / relpath
        if not path.is_file():
            continue
        finding = _scan_file(path, fix_hint)
        if finding is not None:
            findings.append(finding)
    return findings