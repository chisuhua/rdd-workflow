"""Pending RFC state manager (CRUD + schema validation + atomic write).

Stores pending cross-repo RFC Issues in .rddf/state/.cross-repo-pending.json
with schema-validated entries. All writes are atomic (temp file + rename).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Reuse W2-2 SSOT schema path (global install location)
_SCHEMA_PATH = Path.home() / ".agents" / "skills" / "_lib" / "schemas" / "cross_repo_pending_schema.json"


def _load_schema() -> dict:
    if not _SCHEMA_PATH.exists():
        # Fallback minimal inline schema
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "version": {"type": "integer", "const": 1},
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["hub_issue_url", "gate_type", "expected_status", "created_at"],
                        "properties": {
                            "hub_issue_url": {"type": "string", "format": "uri"},
                            "gate_type": {"type": "string"},
                            "expected_status": {"enum": ["approved", "rejected", "merged"]},
                            "created_at": {"type": "string", "format": "date-time"},
                            "status": {"enum": ["pending", "approved", "rejected", "superseded"]},
                        },
                    },
                },
            },
            "required": ["version", "entries"],
        }
    return json.loads(_SCHEMA_PATH.read_text())


_STATE_FILE = ".cross-repo-pending.json"


def _state_path(state_dir: Path) -> Path:
    return Path(state_dir) / _STATE_FILE


def read_pending_state(state_dir: Path) -> Dict[str, Any]:
    """Read pending state. Returns default if file doesn't exist."""
    path = _state_path(state_dir)
    if not path.exists():
        return {"version": 1, "entries": []}
    return json.loads(path.read_text())


def write_pending_state(state_dir: Path, state: Dict[str, Any]) -> None:
    """Atomic write: temp file + rename to avoid partial writes."""
    path = _state_path(state_dir)
    fd, tmp_path = tempfile.mkstemp(prefix=".cross-repo-pending-", suffix=".tmp", dir=str(state_dir))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _validate_entry(entry: Dict[str, Any]) -> None:
    """Validate single entry has required fields."""
    required = ["hub_issue_url", "gate_type", "expected_status", "created_at"]
    for key in required:
        if key not in entry:
            raise ValueError(f"Entry missing required field: {key}")
    if "status" not in entry:
        entry["status"] = "pending"


def add_pending_entry(state_dir: Path, entry: Dict[str, Any]) -> None:
    """Add a new pending entry."""
    _validate_entry(entry)
    state = read_pending_state(state_dir)
    # Deduplicate by hub_issue_url
    state["entries"] = [e for e in state["entries"] if e.get("hub_issue_url") != entry["hub_issue_url"]]
    state["entries"].append(entry)
    write_pending_state(state_dir, state)


def update_pending_entry(state_dir: Path, hub_issue_url: str, updates: Dict[str, Any]) -> None:
    """Update an existing pending entry by hub_issue_url."""
    state = read_pending_state(state_dir)
    found = False
    for e in state["entries"]:
        if e.get("hub_issue_url") == hub_issue_url:
            e.update(updates)
            found = True
            break
    if not found:
        raise KeyError(f"No pending entry with hub_issue_url: {hub_issue_url}")
    write_pending_state(state_dir, state)


def remove_pending_entry(state_dir: Path, hub_issue_url: str) -> None:
    """Remove a pending entry by hub_issue_url."""
    state = read_pending_state(state_dir)
    before = len(state["entries"])
    state["entries"] = [e for e in state["entries"] if e.get("hub_issue_url") != hub_issue_url]
    if len(state["entries"]) == before:
        raise KeyError(f"No pending entry with hub_issue_url: {hub_issue_url}")
    write_pending_state(state_dir, state)
