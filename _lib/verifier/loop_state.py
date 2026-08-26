"""Per-change verifier loop state.

Per fix-rdd-verifier-lifecycle-dashboard Task 2 + ADR-0034 §6:
- Per-change file at .rddf/state/verifier/<change-name>.json
- Schema validated on every save
- Legacy single-file .verifier-loop.json migrates only when its 'change'
  field matches the sole eligible change
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_SCHEMA_PATH = (Path(__file__).resolve().parents[1] / "schemas"
                 / "verifier_loop_schema.json")
_SCHEMA = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))

_VERIFIER_DIR = "verifier"


def _state_path(project_root: Path, change_name: str) -> Path:
    return (Path(project_root) / ".rddf" / "state" / _VERIFIER_DIR
            / f"{change_name}.json")


def _LEGACY_PATH(project_root: Path) -> Path:
    return Path(project_root) / ".rddf" / "state" / ".verifier-loop.json"


def _migrate_legacy(project_root: Path, change_name: str) -> Optional[dict]:
    legacy = _LEGACY_PATH(project_root)
    if not legacy.is_file():
        return None
    try:
        doc = json.loads(legacy.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    if doc.get("change") == change_name:
        return doc
    return None


def init_loop_state(project_root: Path, change_name: str,
                    max_loops: int = 3) -> dict:
    existing = _state_path(project_root, change_name)
    if existing.is_file():
        loaded = load_loop_state(project_root, change_name)
        if loaded is not None:
            return loaded

    migrated = _migrate_legacy(project_root, change_name)
    if migrated is not None:
        migrated["updated_at"] = datetime.now(timezone.utc).isoformat()
        if "verification_state" not in migrated:
            migrated["verification_state"] = "pending"
        save_loop_state(project_root, migrated, change_name)
        return migrated

    state = _new_state(change_name, max_loops)
    save_loop_state(project_root, state, change_name)
    return state


def _new_state(change_name: str, max_loops: int) -> dict:
    return {
        "version": 2,
        "change": change_name,
        "loop_count": 0,
        "max_loops": max_loops,
        "classification_history": [],
        "codebase_commit_at_last_run": "",
        "route": "archive-ready",
        "halt_reason": None,
        "verification_state": "pending",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def load_loop_state(project_root: Path, change_name: str) -> Optional[dict]:
    path = _state_path(Path(project_root), change_name)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def save_loop_state(project_root: Path, state: dict, change_name: str) -> None:
    import jsonschema
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    jsonschema.validate(state, _SCHEMA)

    path = _state_path(Path(project_root), change_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def append_classification(project_root: Path, state: dict, change_name: str,
                          label: str, user_confirmed: bool) -> dict:
    new_state = json.loads(json.dumps(state))
    new_state["classification_history"].append({
        "loop": new_state["loop_count"] + 1,
        "label": label,
        "user_confirmed": user_confirmed,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    new_state["loop_count"] += 1
    save_loop_state(project_root, new_state, change_name)
    return new_state
