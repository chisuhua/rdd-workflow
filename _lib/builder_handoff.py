"""builder-handoff per-change file r/w + FileLock (per spec §6.3 + Oracle H3).

Per-change layout prevents global-file serial-write regression (per ADR-0034 §2).
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from _lib.core.lock import FileLock
from _lib.core.atomic_write import atomic_write_json


def _handoff_path(project_root: str, change_name: str) -> Path:
    return Path(project_root) / ".rddf" / "state" / "builder" / f"{change_name}.json"


def write_builder_handoff(
    project_root: str,
    change_name: str,
    current_phase: str = "phase-0",
    approval_status: str = "pending",
    plan_quality_status: str = "pending",
    execution_mode_decision=None,
    deps_status=None,
    worktree_path: str = "",
    branch: str = "",
    execution_status: str = "pending",
    review_status: str = "pending",
    archive_status: str = "pending",
    verifier_report_path: str = ".rddf/state/.verifier-report.json",
    retry_count: int = 0,
    max_retries: int = 3,
    retry_history=None,
    phase_pause_history=None,
) -> dict:
    if execution_mode_decision is None:
        execution_mode_decision = {}
    if deps_status is None:
        deps_status = {"blockers": [], "manual_deps": [], "cross_repo_pending": []}
    if retry_history is None:
        retry_history = []
    if phase_pause_history is None:
        phase_pause_history = []

    handoff = {
        "schema": "builder-handoff-v1",
        "version": 1,
        "owner": "rdd-builder",
        "change_name": change_name,
        "current_phase": current_phase,
        "approval_status": approval_status,
        "plan_quality_status": plan_quality_status,
        "execution_mode_decision": execution_mode_decision,
        "deps_status": deps_status,
        "worktree_path": worktree_path,
        "branch": branch,
        "execution_status": execution_status,
        "review_status": review_status,
        "retry_count": retry_count,
        "max_retries": max_retries,
        "retry_history": retry_history,
        "phase_pause_history": phase_pause_history,
        "archive_status": archive_status,
        "verifier_report_path": verifier_report_path,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    handoff_path = _handoff_path(project_root, change_name)
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(handoff_path) + ".lock", timeout=10):
        atomic_write_json(str(handoff_path), handoff)
    return handoff


def read_builder_handoff(project_root: str, change_name: str) -> dict:
    handoff_path = _handoff_path(project_root, change_name)
    if not handoff_path.exists():
        return {}
    with open(handoff_path) as f:
        return json.load(f)


def increment_retry(
    project_root: str,
    change_name: str,
    to_phase: str,
    verifier_kind: str,
    verifier_exit_code: int = 1,
) -> dict:
    data = read_builder_handoff(project_root, change_name)
    data["retry_count"] = data.get("retry_count", 0) + 1
    data["current_phase"] = to_phase
    data["retry_history"].append({
        "from_phase": "phase-3",
        "to_phase": to_phase,
        "verifier_exit_code": verifier_exit_code,
        "verifier_kind": verifier_kind,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    valid_kwargs = {
        "current_phase", "approval_status", "plan_quality_status",
        "execution_mode_decision", "deps_status", "worktree_path", "branch",
        "execution_status", "review_status", "archive_status",
        "verifier_report_path", "retry_count", "max_retries",
        "retry_history", "phase_pause_history",
    }
    filtered = {k: v for k, v in data.items() if k in valid_kwargs}
    write_builder_handoff(project_root, change_name, **filtered)
    return data