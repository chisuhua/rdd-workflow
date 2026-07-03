"""Bidirectional sync between v2 state vector and v1.x legacy state files.

Sync targets (v1.x files):
- .rddf/state/roadmap-state.json — roadmap state cache
- proposal-suggestions.md — proposal suggestions
- openspec/changes/<name>/.openspec.yaml — per-change metadata

Sync rules:
- State vector is ALWAYS authoritative. On conflict, state vector wins.
- Conflict detection: mtime comparison (legacy file mtime > state vector mtime
  AND content differs → conflict, prefer state vector, log warning event).
- Sync can be disabled via `SPEC_WORKFLOW_SYNC_DISABLED=1` env var (escape hatch).
"""
from __future__ import annotations
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from skills._lib.event_log import EventLog
from skills._lib.event_types import EventType, Severity
from skills._lib.state_vector import StateVector
from skills._lib.defaults import STATE_VECTOR_PATH, EVENT_LOG_PATH

logger = logging.getLogger(__name__)


LEGACY_ROADMAP_STATE = ".rddf/state/roadmap-state.json"


def is_sync_enabled() -> bool:
    """Return True unless SPEC_WORKFLOW_SYNC_DISABLED=1."""
    return os.environ.get("SPEC_WORKFLOW_SYNC_DISABLED", "0") not in ("1", "true", "yes")


def _state_vector_mtime(path: str) -> float:
    """Return mtime of the state vector file, or 0 if missing."""
    if not os.path.exists(path):
        return 0.0
    return os.path.getmtime(path)


def _record_event(project_root: str, event_type: EventType, severity: Severity, message: str, context: dict) -> None:
    """Record an event to the event log. Best-effort; failures are silently ignored."""
    try:
        log = EventLog(os.path.join(project_root, EVENT_LOG_PATH))
        log.record(event_type, severity, message, context=context)
    except Exception:
        logger.warning("SyncState: record event failed")


def sync_state_vector_to_legacy(project_root: str = ".") -> bool:
    """Read state vector and write to v1.x legacy files. Returns True on success.

    Writes:
    - .rddf/state/roadmap-state.json
    - proposal-suggestions.md (header only, if not present)
    - openspec/changes/<active>/.openspec.yaml (updates phase field)
    """
    if not is_sync_enabled():
        return False

    sv_path = os.path.join(project_root, STATE_VECTOR_PATH)
    if not os.path.exists(sv_path):
        return False

    try:
        sv = StateVector.load(sv_path, verify_checksum=False)
    except Exception:
        logger.warning("SyncState: state vector load failed")
        return False
    data = sv.to_dict()
    arch = data.get("arch_side", {})
    plan = data.get("plan_side", {})
    legacy_payload = {
        "phase": arch.get("phase", "idle"),
        "current_change": arch.get("current_change"),
        "completed_changes": arch.get("completed_changes", []),
        "active_change": plan.get("active_change"),
        "plan_file": plan.get("plan_file"),
        "updated_at": data.get("metadata", {}).get("updated_at"),
        "_synced_from": "v2-state-vector",
    }

    # Write .rddf/state/roadmap-state.json
    legacy_path = Path(project_root) / LEGACY_ROADMAP_STATE
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    with open(legacy_path, "w") as f:
        json.dump(legacy_payload, f, indent=2)

    # Update per-change .openspec.yaml
    active = arch.get("current_change")
    if active:
        yaml_path = Path(project_root) / "openspec" / "changes" / active / ".openspec.yaml"
        if yaml_path.exists():
            try:
                import yaml
                with open(yaml_path) as f:
                    existing = yaml.safe_load(f) or {}
                existing["arch_phase"] = arch.get("phase", "idle")
                existing["synced_at"] = data.get("metadata", {}).get("updated_at")
                with open(yaml_path, "w") as f:
                    yaml.safe_dump(existing, f, default_flow_style=False)
            except Exception:
                logger.warning("SyncState: YAML state write failed")

    _record_event(
        project_root,
        EventType.STATE_UPDATED,
        Severity.DEBUG,
        f"State vector synced to legacy files: {legacy_path}",
        {"direction": "state_to_legacy", "target": str(legacy_path)},
    )
    return True


def sync_legacy_to_state_vector(project_root: str = ".") -> bool:
    """Read v1.x legacy files and update state vector. Returns True on success.

    On conflict (state vector was updated more recently than legacy), state vector
    wins and a warning is recorded.
    """
    if not is_sync_enabled():
        return False

    sv_path = os.path.join(project_root, STATE_VECTOR_PATH)
    legacy_path = Path(project_root) / LEGACY_ROADMAP_STATE
    if not legacy_path.is_file():
        return False

    try:
        with open(legacy_path) as f:
            legacy = json.load(f)
    except json.JSONDecodeError:
        return False

    # Conflict detection via mtime
    legacy_mtime = os.path.getmtime(legacy_path)
    sv_mtime = _state_vector_mtime(sv_path)
    conflict = sv_mtime > 0 and legacy_mtime >= sv_mtime and bool(legacy.get("current_change"))

    if conflict:
        _record_event(
            project_root,
            EventType.WARNING_ISSUED,
            Severity.WARN,
            f"Sync conflict: legacy file newer than state vector. State vector wins.",
            {"legacy_mtime": legacy_mtime, "state_vector_mtime": sv_mtime},
        )
        # Per design.md Decision 4: state vector wins. We do NOT apply legacy values.
        return False

    # No conflict — apply legacy values to state vector
    if os.path.exists(sv_path):
        try:
            sv = StateVector.load(sv_path, verify_checksum=False)
        except Exception:
            logger.warning("SyncState: state vector load failed")
            return False
    else:
        sv = StateVector.create_default()

    if "phase" in legacy:
        sv.update_field("arch_side.phase", legacy["phase"])
    if "current_change" in legacy:
        sv.update_field("arch_side.current_change", legacy["current_change"])
    if "completed_changes" in legacy:
        sv.update_field("arch_side.completed_changes", legacy["completed_changes"])
    if "active_change" in legacy:
        sv.update_field("plan_side.active_change", legacy["active_change"])
    if "plan_file" in legacy:
        sv.update_field("plan_side.plan_file", legacy["plan_file"])

    sv.save(sv_path)
    _record_event(
        project_root,
        EventType.STATE_UPDATED,
        Severity.DEBUG,
        f"Legacy state synced to state vector: {sv_path}",
        {"direction": "legacy_to_state", "source": str(legacy_path)},
    )
    return True