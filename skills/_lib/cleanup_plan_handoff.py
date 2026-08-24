"""Plan-handoff cleanup with final-state convergence semantics.

Fix-adr-0027-clean-stale-plan-handoff-on-ship-done: the inline Python
block in ``skills/guide-ship/scripts/ship_archive.sh::cleanup_plan_handoff``
previously only updated active_changes / archived_changes but never reset
``current_change`` or ``ship_started_at`` → stale state repeated on every
ship-done entry.

This module extracts the logic so it's unit-testable. The bash inline
block now calls this via python3 -c.

**Convergence semantics** (the reason for extraction):
  - active_changes == 0  ⇒  current_change is None (cleared in branch 2)
  - active_changes == 0  ⇒  ship_started_at is None (cleared in branch 3)
  - execution_mode_decisions is NEVER cleared (historical record)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def cleanup_plan_handoff(handoff_path: Path, change_name: str) -> None:
    """Update plan-handoff.json after archiving a change.

    Branches:
      1. active_changes decrements (saturating at 0, never negative)
      2. If change_name == current_change → set current_change = None
      3. If active_changes reaches 0 → set ship_started_at = None
      4. archived_changes appends change_name
      5. execution_mode_decisions preserved (historical)

    Also writes ``archived_at`` timestamp per archive record.

    Idempotent: missing file → return without error.
    """
    handoff_path = Path(handoff_path)
    if not handoff_path.is_file():
        return  # Scenario 5: idempotent skip

    data = json.loads(handoff_path.read_text())

    # Record archive timestamp
    data["archived_at"] = datetime.now(timezone.utc).isoformat()

    # Branch 1: decrement active_changes (saturating)
    active = data.get("active_changes", 0)
    if isinstance(active, int) and active > 0:
        data["active_changes"] = active - 1
    else:
        data["active_changes"] = 0

    # Branch 2: clear current_change if matching
    if data.get("current_change") == change_name:
        data["current_change"] = None

    # Branch 3: clear ship_started_at when no active changes
    if data["active_changes"] == 0:
        data["ship_started_at"] = None
        data["last_ship_completed_at"] = datetime.now(timezone.utc).isoformat()

    # Branch 4: append to archived_changes
    if "archived_changes" not in data:
        data["archived_changes"] = []
    if change_name not in data["archived_changes"]:
        data["archived_changes"].append(change_name)

    handoff_path.write_text(json.dumps(data, indent=2))