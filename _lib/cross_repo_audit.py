"""Cross-repo audit log (JSONL append with validation).

Writes to .rddf/state/.cross-repo-audit.jsonl. Each entry has required
fields: timestamp, proposal_name, hub_issue, approver, decision.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Union

PathLike = Union[str, Path]

AUDIT_LOG_FIELDS = ("timestamp", "proposal_name", "hub_issue", "approver", "decision")


def validate_entry(entry: Dict[str, Any]) -> None:
    """Raise ValueError if entry is missing required fields."""
    missing = [f for f in AUDIT_LOG_FIELDS if f not in entry]
    if missing:
        raise ValueError(f"audit log entry missing required fields: {missing}")


def append_audit_log_entry(path: PathLike, entry: Dict[str, Any]) -> None:
    """Append one JSONL line. Auto-creates parent dir."""
    validate_entry(entry)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if "timestamp" not in entry:
        entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    with p.open("a") as f:
        f.write(json.dumps(entry) + "\n")
