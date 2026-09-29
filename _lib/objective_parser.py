"""Collect active/deferred objectives as JSON for LLM handoff payloads.

Bug X3 fix: planner_stage_entry.sh and planner_stage_exit.sh each contained
~45 lines of identical inline Python that parsed objectives and serialized
them as JSON. This module consolidates that logic into a single source of
truth so the two stage scripts (and any future consumer) share one
implementation.

Output shape (JSON array of records):
    [{
        "id": "objective-xxx",
        "priority": "P0|P1|P2",
        "status": "active|deferred",
        "review_by": "YYYY-MM-DD",
        "theme": "<truncated to 200 chars>",
        "next_sprint_candidates": ["candidate A", "candidate B", ...]
    }]

Returns the JSON string (not a list) so shell scripts can substitute it
directly into environment variables without extra serialization steps.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

THEME_MAX_LEN = 200


def collect_active_objectives(project_root: Path | str) -> str:
    """Return JSON string of active/deferred objectives for LLM consumption.

    Empty string if no objectives dir exists or any error occurs (graceful
    degradation; matches prior inline-Python behavior).

    Skips:
    - Files in `.rddf/roadmap/objectives/archive/` subdirectory
    - Files that fail to parse (malformed frontmatter, IO errors)
    - Statuses other than `active` or `deferred`

    Filters from `next_sprint_candidates`:
    - Lines starting with `N/A` (deferred marker per D9)
    - Empty lines
    """
    project_root = Path(project_root)
    obj_dir = project_root / ".rddf" / "roadmap" / "objectives"
    if not obj_dir.is_dir():
        return "[]"

    sys.path.insert(0, str(project_root))
    try:
        from _lib.objective import parse_objective
    except ImportError:
        return "[]"

    records: list[dict[str, Any]] = []
    for f in sorted(obj_dir.glob("*.md")):
        if f.parent.name == "archive":
            continue
        try:
            data = parse_objective(f)
        except (ValueError, OSError):
            continue
        fm = data.get("frontmatter", {})
        if fm.get("status") not in ("active", "deferred"):
            continue
        records.append({
            "id": fm.get("id", f.stem),
            "priority": fm.get("priority", "?"),
            "status": fm.get("status", "?"),
            "review_by": fm.get("review_by", ""),
            "theme": fm.get("theme", "")[:THEME_MAX_LEN],
            "next_sprint_candidates": _parse_candidates(data),
        })

    return json.dumps(records, ensure_ascii=False)


def _parse_candidates(data: dict[str, Any]) -> list[str]:
    """Extract next_sprint_candidates from §10, filtering N/A markers."""
    candidates: list[str] = []
    sec10 = data.get("sections", {}).get("## 10.", "")
    for line in sec10.splitlines():
        s = line.strip()
        if s.startswith("- [ ]"):
            candidates.append(s[5:].strip())
        elif s.startswith("- "):
            candidates.append(s[2:].strip())
    return [c for c in candidates if c and not c.startswith("N/A")]
