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

# Match a markdown table row like `| [name](.rddf/improvements/<file>.md) | ...`.
# Only used inside proposal-approved.md (and similar tables), so the
# <a href=".rddf/improvements/` anchor is enough to avoid false positives in body prose.
_ROW_RE = re.compile(r"\|\s*\[([^\]]+)\]\(\s*.rddf/improvements/[^)]+\)")


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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: parse_approved.py <path-to-proposal-approved.md>", file=sys.stderr)
        sys.exit(2)
    for name in parse_approved_proposals(sys.argv[1]):
        print(name)