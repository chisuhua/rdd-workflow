""".verifier-loop.json load/save with schema validation.

Per ADR-0034 §6: tracks loop count, classification history, route, halt reason.
Schema validated on every save to prevent silent corruption.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_SCHEMA_PATH = (Path(__file__).resolve().parents[1] / "schemas"
                 / "verifier_loop_schema.json")
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def _state_path(project_root: Path) -> Path:
    return project_root / ".rddf" / "state" / ".verifier-loop.json"


def init_loop_state(project_root: Path, change_name: str,
                    max_loops: int = 3) -> dict:
    """Initialize a new loop state for a change. Persists to disk.

    Default status="archive-ready" until classification append changes route.

    Args:
        project_root: Path to project root.
        change_name: OpenSpec change name.
        max_loops: Maximum retry attempts before halt.

    Returns:
        The initialized state dict.
    """
    state = {
        "version": 1,
        "change": change_name,
        "loop_count": 0,
        "max_loops": max_loops,
        "classification_history": [],
        "codebase_commit_at_last_run": "",
        "route": "archive-ready",
        "halt_reason": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_loop_state(project_root, state)
    return state


def load_loop_state(project_root: Path) -> Optional[dict]:
    """Load loop state. Returns None if missing or corrupt."""
    path = _state_path(Path(project_root))
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def save_loop_state(project_root: Path, state: dict) -> None:
    """Save loop state. Validates against schema before writing.

    Args:
        project_root: Path to project root.
        state: Loop state dict to persist.

    Raises:
        jsonschema.ValidationError: if state fails schema validation.
        OSError: if .rddf/state/ cannot be written.
    """
    import jsonschema
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    jsonschema.validate(state, _SCHEMA)

    path = _state_path(Path(project_root))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def append_classification(project_root: Path, state: dict, label: str,
                          user_confirmed: bool) -> dict:
    """Append a classification to history and increment loop_count.

    Args:
        project_root: Where to persist.
        state: Current loop state (will be deep-copied).
        label: "implementation_gap" or "proposal_drift".
        user_confirmed: True if user agreed with AI label, False if overridden.

    Returns:
        Updated state (also persisted to disk).
    """
    new_state = json.loads(json.dumps(state))  # deep copy
    new_state["classification_history"].append({
        "loop": new_state["loop_count"] + 1,
        "label": label,
        "user_confirmed": user_confirmed,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    new_state["loop_count"] += 1
    save_loop_state(project_root, new_state)
    return new_state