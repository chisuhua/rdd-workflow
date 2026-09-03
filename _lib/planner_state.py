"""Planner state I/O — atomic read/write of .rddf/state/.planner-state.json.

This module is the single source of truth for `rdd-planner` runtime
state. All writes are atomic via `_lib.core.atomic_write` and
serialized via `_lib.core.lock.FileLock` to prevent the corruption
mode seen in `.rddf/state/iteration.corrupt.*`.
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict

import jsonschema

from _lib.core.atomic_write import atomic_write_json
from _lib.core.lock import FileLock

__all__ = [
    "PlannerStateError",
    "SchemaMismatchError",
    "current_sprint_id",
    "read_state",
    "write_state",
    "STATE_FILENAME",
    "SCHEMA_VERSION",
    "STATE_SCHEMA_PATH",
]

STATE_FILENAME = ".planner-state.json"
STATE_SCHEMA_PATH = Path(__file__).parent / "schemas" / "planner_state_schema.json"
SCHEMA_VERSION = 1


class PlannerStateError(Exception):
    """Base error for planner_state."""


class SchemaMismatchError(PlannerStateError):
    """State file version does not match SCHEMA_VERSION."""


def current_sprint_id() -> str:
    """Return current sprint id (sprint-YYYY-MM) based on local time."""
    now = _dt.datetime.now()
    return f"sprint-{now.year:04d}-{now.month:02d}"


def _state_path(project_root: Path) -> Path:
    return project_root / ".rddf" / "state" / STATE_FILENAME


def _default_state() -> Dict[str, Any]:
    """Return a fresh, empty state dict."""
    return {
        "version": SCHEMA_VERSION,
        "current_sprint": current_sprint_id(),
        "last_sync_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "last_sync_status": "ok",
        "active_projects": [],
        "unmapped_proposals": [],
        "synced_proposals": [],
    }


def read_state(project_root: Path, *, validate: bool = True) -> Dict[str, Any]:
    """Read planner state. Returns default empty state if file missing.

    Args:
        project_root: Absolute path to project root.
        validate: If True (default), validate against schema after load.

    Returns:
        State dict.

    Raises:
        SchemaMismatchError: If state version != SCHEMA_VERSION.
    """
    path = _state_path(project_root)
    if not path.exists():
        return _default_state()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("version") != SCHEMA_VERSION:
        raise SchemaMismatchError(
            f"State version {data.get('version')} != expected {SCHEMA_VERSION}. "
            f"Delete {path} to reset."
        )
    if validate:
        schema = json.loads(STATE_SCHEMA_PATH.read_text())
        jsonschema.validate(data, schema)
    return data


def write_state(project_root: Path, state: Dict[str, Any], *, validate: bool = True) -> None:
    """Atomically write planner state.

    Args:
        project_root: Absolute path to project root.
        state: State dict (must conform to schema).
        validate: If True (default), validate before write.

    Raises:
        PlannerStateError: Validation failure.
    """
    if validate:
        schema = json.loads(STATE_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(state, schema)
        except jsonschema.ValidationError as exc:
            raise PlannerStateError(f"State validation failed: {exc.message}") from exc

    path = _state_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")

    with FileLock(str(lock_path), timeout=10.0):
        atomic_write_json(path, state)