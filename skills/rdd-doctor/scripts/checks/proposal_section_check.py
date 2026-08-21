"""Cat 9 — Detect proposal drift between proposal-approved.md "## 已批准提案"
section and openspec/changes/archive/ directory.

Bug fixed: fix-proposal-approved-sync (P2, 2026-08-21). Before this check,
`state.sh::sweep_implemented_proposals` was defined but never wired into the
archive flow. Result: archived proposals stayed in the "approved" section
forever, and dashboards showed "not yet implemented" for already-archived
changes. This category catches that drift at audit time.

CRITICAL (not WARNING) because the dashboard's "approved proposals" count
LIES when this is broken — the user makes decisions based on incorrect data.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity


_NAME_PATTERN = re.compile(r"\|\s*\[([^\]]+)\]\(\s*\.rddf/improvements/[^)]+\)")
_ARCHIVE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}-(.+)$")


def _parse_approved_section(content: str) -> List[str]:
    """Return proposal names under the ## 已批准提案 section.

    Stops at the next level-2 heading. Includes overflow rows that sit
    between sections (the parser at `_lib/parse_approved.py` does the same).
    """
    in_section = False
    names: List[str] = []
    for line in content.splitlines():
        if line.startswith("## 已批准提案"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section:
            continue
        m = _NAME_PATTERN.search(line)
        if m:
            names.append(m.group(1).strip())
    return names


def _list_archive_names(project_root: Path) -> set[str]:
    """Return the set of proposal names that have an archive/<date>-<name>/ dir."""
    archive_dir = project_root / "openspec" / "changes" / "archive"
    if not archive_dir.is_dir():
        return set()
    names: set[str] = set()
    for entry in os.listdir(archive_dir):
        m = _ARCHIVE_PATTERN.match(entry)
        if m:
            names.add(m.group(1))
    return names


def run(project_root: Path | None = None) -> List[Finding]:
    """Run proposal-section check against project_root."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings: List[Finding] = []

    approved_path = project_root / "proposal-approved.md"
    if not approved_path.is_file():
        return findings

    content = approved_path.read_text(encoding="utf-8")
    approved_names = _parse_approved_section(content)
    archive_names = _list_archive_names(project_root)

    for name in approved_names:
        if name in archive_names:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="proposal-section",
                file="proposal-approved.md",
                line=None,
                snippet=(
                    f"'{name}' is in '## 已批准提案' but "
                    f"openspec/changes/archive/<date>-{name}/ exists"
                ),
                fix_hint=(
                    "run sweep_implemented_proposals (from _lib/state.sh) "
                    "or archive a new change to trigger the post_archive_cleanup hook"
                ),
            ))

    return findings
