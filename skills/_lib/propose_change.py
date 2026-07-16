"""skills/_lib/propose_change.py — helpers for propose.md Phase 4.

Extracted from inline PYEOF heredocs in propose.md lines 443-796
(P0-1 refactor, Metis plan 2026-07-16). Each function preserves the
exact behavior of the corresponding inline block, including output
strings and exception handling.
"""

import json
import os
from typing import Optional


def set_suggestion_status(
    project_root: str, name: str, new_status: str
) -> bool:
    """Update status field for matching entry in proposal-suggestions.md.

    Returns True if updated, False if file missing / malformed / name not found.
    Preserves all other fields. Matches original lines 531-548 inline behavior.
    """
    path = os.path.join(project_root, "proposal-suggestions.md")
    try:
        with open(path) as f:
            entries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    if not isinstance(entries, list):
        return False
    updated = False
    for entry in entries:
        if isinstance(entry, dict) and entry.get("name") == name:
            entry["status"] = new_status
            updated = True
    if updated:
        try:
            with open(path, "w") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except OSError:
            return False
    return updated