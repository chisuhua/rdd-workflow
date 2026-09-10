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
    dispatch_quick_at=None,
    dispatch_quick_outcome=None,
    dispatch_quick_review=None,
) -> dict:
    """Write per-change builder-handoff v1.1 (per ADR-0048, dispatch-quick fields).

    approval_status enum (per spec §6.3 + ADR-0048):
        pending | approved | rejected | deferred | revising | dispatched_to_quick

    dispatch_quick_at: ISO timestamp when P0 选项 5 触发 (per ADR-0048 §Decision 3)
    dispatch_quick_outcome: enum completed | escalated | unverified (after rdd-quick P4)
    dispatch_quick_review: LLM hidden complexity check (per ADR-0049 §Decision 5)
        dict with fields:
          complexity_confirmed: simple | complex | unknown
          concerns: list[str]
          suggested_action: proceed | escalate
          reviewed_at: ISO timestamp
          data_source: absolute path of improvement file
          forced_by_user: bool (optional, true if user overrode complex warning)
    """
    if execution_mode_decision is None:
        execution_mode_decision = {}
    if deps_status is None:
        deps_status = {"blockers": [], "manual_deps": [], "cross_repo_pending": []}
    if retry_history is None:
        retry_history = []
    if phase_pause_history is None:
        phase_pause_history = []

    # ADR-0048: validate approval_status enum; backward compat: existing values allowed
    valid_approval = {"pending", "approved", "rejected", "deferred", "revising", "dispatched_to_quick"}
    if approval_status not in valid_approval:
        raise ValueError(
            f"approval_status must be one of {valid_approval}, got {approval_status!r}"
        )

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
    # ADR-0048 §Decision 3: dispatch-quick tracking fields (optional; only set when used)
    if dispatch_quick_at is not None:
        handoff["dispatch_quick_at"] = dispatch_quick_at
    if dispatch_quick_outcome is not None:
        if dispatch_quick_outcome not in {"completed", "escalated", "unverified"}:
            raise ValueError(
                f"dispatch_quick_outcome must be completed|escalated|unverified, "
                f"got {dispatch_quick_outcome!r}"
            )
        handoff["dispatch_quick_outcome"] = dispatch_quick_outcome
    # ADR-0049 §Decision 5: LLM hidden complexity check (optional; only set when LLM review ran)
    if dispatch_quick_review is not None:
        _validate_dispatch_quick_review(dispatch_quick_review)
        handoff["dispatch_quick_review"] = dispatch_quick_review

    handoff_path = _handoff_path(project_root, change_name)
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(handoff_path) + ".lock", timeout=10):
        atomic_write_json(str(handoff_path), handoff)
    return handoff


def _validate_dispatch_quick_review(review) -> None:
    """Validate dispatch_quick_review schema (per ADR-0049).

    Raises ValueError on invalid fields. The review dict is mutated to
    normalize reviewed_at if absent.
    """
    if not isinstance(review, dict):
        raise ValueError(
            f"dispatch_quick_review must be dict, got {type(review).__name__}"
        )

    valid_complexity = {"simple", "complex", "unknown"}
    valid_action = {"proceed", "escalate"}

    complexity = review.get("complexity_confirmed")
    if complexity is None:
        raise ValueError(
            "dispatch_quick_review requires complexity_confirmed field "
            f"(one of {valid_complexity})"
        )
    if complexity not in valid_complexity:
        raise ValueError(
            f"dispatch_quick_review.complexity_confirmed must be one of "
            f"{valid_complexity}, got {complexity!r}"
        )

    action = review.get("suggested_action")
    if action is None:
        raise ValueError(
            "dispatch_quick_review requires suggested_action field "
            f"(one of {valid_action})"
        )
    if action not in valid_action:
        raise ValueError(
            f"dispatch_quick_review.suggested_action must be one of "
            f"{valid_action}, got {action!r}"
        )

    concerns = review.get("concerns", [])
    if not isinstance(concerns, list):
        raise ValueError(
            f"dispatch_quick_review.concerns must be list, got {type(concerns).__name__}"
        )
    for i, c in enumerate(concerns):
        if not isinstance(c, str):
            raise ValueError(
                f"dispatch_quick_review.concerns[{i}] must be str, got {type(c).__name__}"
            )

    if "reviewed_at" not in review:
        review["reviewed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_builder_handoff(project_root: str, change_name: str) -> dict:
    handoff_path = _handoff_path(project_root, change_name)
    if not handoff_path.exists():
        return {}
    with open(handoff_path) as f:
        return json.load(f)


def update_builder_handoff(project_root: str, change_name: str, **partial) -> dict:
    """Merge partial fields into existing handoff; auto-include required fields.

    Single-call update API that replaces the dangerous pattern of
    ``write_builder_handoff(**read_builder_handoff(...))``. Reads the
    current handoff, merges ``partial`` on top, and writes back atomically
    under FileLock. Auto-generated fields (schema, version, owner,
    updated_at) are preserved from the existing handoff or filled in
    from defaults.

    Returns the merged dict.
    """
    existing = read_builder_handoff(project_root, change_name)
    merged = {**existing, **partial}
    merged.setdefault("schema", "builder-handoff-v1")
    merged.setdefault("version", 1)
    merged.setdefault("owner", "rdd-builder")
    merged.setdefault("change_name", change_name)
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()

    handoff_path = _handoff_path(project_root, change_name)
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(handoff_path) + ".lock", timeout=10):
        atomic_write_json(str(handoff_path), merged)
    return merged


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
    data.setdefault("retry_history", []).append({
        "from_phase": "phase-3",
        "to_phase": to_phase,
        "verifier_exit_code": verifier_exit_code,
        "verifier_kind": verifier_kind,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    data.pop("change_name", None)
    data.pop("schema", None)
    data.pop("version", None)
    data.pop("owner", None)
    data.pop("updated_at", None)
    return update_builder_handoff(project_root, change_name, **data)