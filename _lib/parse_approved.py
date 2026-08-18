"""Centralized parser for proposal-approved.md.

Reads BOTH the `## 已批准提案` and `## 已实施` sections and returns
approved proposal names, deduplicated, in file-appearance order.

Design choice: full-file regex matching of the row pattern
`| [name](.rddf/improvements/<file>.md) | ... |`. The `已批准提案` section holds
approved-but-not-implemented entries; `已实施` holds approved-and-implemented
entries. Historical proposals were archived directly after approval, so
`已批准提案` is often empty in practice — parsers that only read the region
before `## 已实施` silently see zero approved entries (this was the bug).

This helper is the single source of truth for approved-name extraction. It
complements `detect-suggestions-approved-inconsistency` (which fixed the
data-view consistency between suggestions/approved, not the parsing logic
itself).

CLI mode (for bash invocation):

    python3 _lib/parse_approved.py <path-to-proposal-approved.md>

prints each name on its own line, in file-appearance order, deduplicated.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple, Optional

# Match a markdown table row like `| [name](.rddf/improvements/<file>.md) | ...`.
# Only used inside proposal-approved.md (and similar tables), so the
# <a href=".rddf/improvements/` anchor is enough to avoid false positives in body prose.
_ROW_RE = re.compile(r"\|\s*\[([^\]]+)\]\(\s*.rddf/improvements/[^)]+\)")

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")

_APPROVED_SECTION = "已批准提案"
_IMPLEMENTED_SECTION = "已实施"


class ApprovedRow(NamedTuple):
    """One parsed row from proposal-approved.md.

    Fields:
        name: Proposal name (from the markdown link text).
        priority: P0/P1/P2/P3 string, or None when the column is missing.
        date: Date string from the third column, or None. Section-specific:
            "approved" rows carry approval date, "implemented" rows carry
            completion date.
        section: "approved" (尚未实施) or "implemented" (已完成归档).
    """

    name: str
    priority: Optional[str]
    date: Optional[str]
    section: str


def parse_approved_proposals(path: str) -> list[str]:
    """Return approved proposal names from both sections of proposal-approved.md.

    Args:
        path: Filesystem path to proposal-approved.md.

    Returns:
        Proposal names in file-appearance order, deduplicated. Empty list
        when the file is missing, unreadable, or has no matching rows.
    """
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    seen: set[str] = set()
    names: list[str] = []
    for match in _ROW_RE.finditer(content):
        name = match.group(1).strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def parse_approved_proposals_detailed(path: str) -> list[ApprovedRow]:
    """Return one ``ApprovedRow`` per table row, preserving section context.

    Walks the file linearly so we can attribute each row to the section
    heading that precedes it. Rows outside ``## 已批准提案`` /
    ``## 已实施`` (e.g., rows in supersedes callouts, dependency notes)
    are skipped — those rows are not part of the canonical approval log.

    Backward compat: if the file has NO ``## 已批准提案`` or ``## 已实施``
    heading at all (legacy / minimal-format files), every matching table
    row is attributed to ``"approved"`` so callers continue to see what
    they used to. The ``parse_approved_proposals()`` legacy helper had no
    section awareness; this fallback preserves that contract.

    The two sections have slightly different column layouts in practice:
    ``## 已批准提案`` uses 4 columns (提案 / 优先级 / 批准时间 / 批准者),
    ``## 已实施`` uses 3 columns (提案 / 优先级 / 完成时间). The parser
    captures whichever cells exist; missing cells become ``None``.

    Args:
        path: Filesystem path to proposal-approved.md.

    Returns:
        List of ``ApprovedRow`` in file-appearance order, deduplicated by
        name (first occurrence wins). Empty list when the file is missing,
        unreadable, or has no matching rows.
    """
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    rows: list[ApprovedRow] = []
    seen: set[str] = set()
    section_tag: Optional[str] = None
    has_any_heading = False
    has_canonical_heading = False

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        section_match = _SECTION_RE.match(line)
        if section_match:
            heading = section_match.group(1).strip()
            has_any_heading = True
            if heading == _APPROVED_SECTION:
                section_tag = "approved"
                has_canonical_heading = True
            elif heading == _IMPLEMENTED_SECTION:
                section_tag = "implemented"
                has_canonical_heading = True
            else:
                section_tag = None
            continue

        # Legacy fallback: only when the file has no headings at all.
        if (
            not has_any_heading
            and section_tag is None
            and not has_canonical_heading
        ):
            section_tag = "approved"

        if section_tag is None:
            continue

        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        if len(cells) < 2:
            continue

        full_match = _ROW_RE.search(line)
        if not full_match:
            continue
        name = full_match.group(1).strip()
        if not name or name in seen:
            continue
        seen.add(name)

        priority = cells[1] if len(cells) >= 2 and cells[1] else None
        date = cells[2] if len(cells) >= 3 and cells[2] else None

        rows.append(
            ApprovedRow(
                name=name,
                priority=priority,
                date=date,
                section=section_tag,
            )
        )

    return rows


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: parse_approved.py <path-to-proposal-approved.md>", file=sys.stderr)
        sys.exit(2)
    for name in parse_approved_proposals(sys.argv[1]):
        print(name)