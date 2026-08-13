"""Cat 4 — Validate proposal-suggestions.md and proposal-approved.md Markdown tables.

Uses a lightweight inline parser to avoid circular dependency on
_lib/parse_approved.py (which lives in a separate worktree change
fix-design-proposal-review-approved-parsing). After that change merges,
this module can be migrated to reuse that parser.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity


_FILES = ["proposal-suggestions.md", "proposal-approved.md"]
_EXPECTED_COLUMNS = {
    "proposal-suggestions.md": 5,
    "proposal-approved.md": 4,
}
_ROW_PATTERN = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)]+)\)\s*\|")


def _count_columns(line: str) -> int:
    """Count cell separators in a Markdown table row."""
    return line.count("|") - 1


def run(project_root: Path | None = None) -> List[Finding]:
    """Run cat-4 against project_root."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings: List[Finding] = []

    for fname in _FILES:
        path = project_root / fname
        if not path.is_file():
            continue
        expected_cols = _EXPECTED_COLUMNS[fname]
        lines = path.read_text().splitlines()
        line_no = 0
        in_data = False
        for raw in lines:
            line_no += 1
            stripped = raw.strip()
            if stripped.startswith("|------") or stripped.startswith("| ---"):
                in_data = True
                continue
            if not in_data or not stripped.startswith("|"):
                continue
            m = _ROW_PATTERN.match(stripped)
            if not m:
                continue
            link_target = m.group(2)
            cols = _count_columns(stripped)
            if cols != expected_cols:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category="proposal-table",
                    file=fname,
                    line=line_no,
                    snippet=f"row has {cols} columns, expected {expected_cols}",
                    fix_hint="add/remove columns to match expected schema",
                ))
            if link_target.startswith(".rddf/improvements/"):
                if not (project_root / link_target).is_file():
                    findings.append(Finding(
                        severity=Severity.WARNING,
                        category="proposal-table",
                        file=fname,
                        line=line_no,
                        snippet=f"broken link to {link_target}",
                        fix_hint="verify the .rddf/improvements file exists or remove this row",
                    ))
            elif link_target.startswith("improvements/") or "/" not in link_target:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category="proposal-table",
                    file=fname,
                    line=line_no,
                    snippet=f"non-canonical link to {link_target} (use .rddf/improvements/<name>.md)",
                    fix_hint="migrate file to .rddf/improvements/ and update link to canonical prefix",
                ))

    return findings