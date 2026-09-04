"""Stage 3 Change 2: persistent planner review-task storage.

Owner: rdd-planner. Read by rdd-arch Phase 1 + rddf planner feedback CLI.

Per ADR-0042: this is an INDEPENDENT file (not embedded in .arch-handoff.json)
to maintain ADR-0028 role boundaries — planner owns, arch consumes.

Schema: planner-feedback-v1 (see _lib/schemas/planner_feedback_schema.json)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from _lib.core.atomic_write import atomic_write_json
from _lib.core.lock import FileLock

__all__ = [
    "FeedbackEntry",
    "compute_fingerprint",
    "compute_summary",
    "compute_planner_feedback",
    "read_planner_feedback",
    "read_planner_feedback_unlocked",
    "write_planner_feedback",
    "acknowledge_feedback",
    "resolve_feedback",
    "dismiss_feedback",
    "prune_resolved_feedback",
    "FILENAME",
    "LOCK_FILENAME",
]

FILENAME = ".planner-feedback.json"
LOCK_FILENAME = ".planner-feedback.json.lock"

VALID_KINDS = {"unmapped_proposal", "coverage_gap", "adr_drift", "roadmap_staleness"}
VALID_SEVERITIES = {"critical", "warning", "info"}
VALID_STATUSES = {"open", "acknowledged", "resolved", "dismissed"}


@dataclass
class FeedbackEntry:
    feedback_id: str
    kind: str
    severity: str
    status: str
    fingerprint: str
    proposal: str
    theme: str
    related_adr_ids: List[str]
    message: str
    suggested_action: str
    created_at: str
    last_seen_at: str
    acknowledged_at: Optional[str]
    resolved_at: Optional[str]
    resolved_by: Optional[str]
    dismissed_at: Optional[str]
    dismissed_by: Optional[str]
    computed_from: Dict[str, Any]
    stale: bool = False

    def __post_init__(self):
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {VALID_SEVERITIES}, got {self.severity!r}")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}, got {self.status!r}")
        if self.kind not in VALID_KINDS:
            raise ValueError(f"kind must be one of {VALID_KINDS}, got {self.kind!r}")


def compute_fingerprint(
    kind: str,
    proposal: str,
    theme: str,
    related_adr_ids: List[str],
    reason: str,
) -> str:
    """Deterministic 16-char fingerprint from semantic inputs.

    Same proposal+theme+reason+kind → same fingerprint (idempotent compute).
    """
    canonical = json.dumps(
        {
            "kind": kind,
            "proposal": proposal,
            "theme": theme,
            "related_adr_ids": sorted(related_adr_ids),
            "reason": reason,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def compute_summary(entries: List[FeedbackEntry]) -> Dict[str, int]:
    """Compute status distribution summary from feedback list."""
    s = {
        "open_critical": 0,
        "open_warning": 0,
        "open_info": 0,
        "acknowledged": 0,
        "resolved": 0,
        "dismissed": 0,
    }
    for e in entries:
        if e.status == "open":
            if e.severity == "critical":
                s["open_critical"] += 1
            elif e.severity == "warning":
                s["open_warning"] += 1
            elif e.severity == "info":
                s["open_info"] += 1
        elif e.status in ("acknowledged", "resolved", "dismissed"):
            s[e.status] += 1
    return s


def _feedback_path(project_root: str) -> str:
    return os.path.join(project_root, ".rddf", "state", FILENAME)


def _lock_path(project_root: str) -> str:
    return os.path.join(project_root, ".rddf", "state", LOCK_FILENAME)


def read_planner_feedback_unlocked(project_root: str) -> Dict[str, Any]:
    """Read .planner-feedback.json WITHOUT acquiring FileLock.

    Use only inside an outer FileLock critical section. Otherwise races
    with concurrent writers are possible. See read_planner_feedback
    for the locked equivalent.
    """
    path = _feedback_path(project_root)
    if not os.path.exists(path):
        return _empty_schema(project_root)
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _empty_schema(project_root)


def _write_planner_feedback_unlocked(project_root: str, data: Dict[str, Any]) -> None:
    """Write .planner-feedback.json via atomic_write_json WITHOUT FileLock.

    Use only inside an outer FileLock critical section (FileLock is
    fcntl.flock per-fd, non-reentrant — see write_planner_feedback).
    """
    state_dir = os.path.join(project_root, ".rddf", "state")
    os.makedirs(state_dir, exist_ok=True)
    path = _feedback_path(project_root)
    atomic_write_json(path, data, indent=2, ensure_ascii=False)


def read_planner_feedback(project_root: str) -> Dict[str, Any]:
    """Read .planner-feedback.json under FileLock. Returns empty schema if absent/corrupted."""
    lock = _lock_path(project_root)
    with FileLock(lock, timeout=10.0):
        return read_planner_feedback_unlocked(project_root)


def write_planner_feedback(project_root: str, data: Dict[str, Any]) -> None:
    """Write .planner-feedback.json under FileLock + atomic_write_json."""
    lock = _lock_path(project_root)
    with FileLock(lock, timeout=10.0):
        _write_planner_feedback_unlocked(project_root, data)


def acknowledge_feedback(project_root: str, feedback_id: str) -> bool:
    """Transition feedback to acknowledged status. Returns True if found and updated."""
    lock = _lock_path(project_root)
    with FileLock(lock, timeout=10.0):
        data = read_planner_feedback_unlocked(project_root)
        updated = False
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for entry in data.get("feedbacks", []):
            if entry["feedback_id"] == feedback_id and entry["status"] == "open":
                entry["status"] = "acknowledged"
                entry["acknowledged_at"] = now
                updated = True
                break
        if updated:
            data["summary"] = compute_summary([FeedbackEntry(**e) for e in data["feedbacks"]])
            _write_planner_feedback_unlocked(project_root, data)
        return updated


def resolve_feedback(project_root: str, feedback_id: str, by: str = "architect") -> bool:
    """Transition feedback to resolved status. Returns True if found and updated."""
    lock = _lock_path(project_root)
    with FileLock(lock, timeout=10.0):
        data = read_planner_feedback_unlocked(project_root)
        updated = False
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for entry in data.get("feedbacks", []):
            if entry["feedback_id"] == feedback_id and entry["status"] in ("open", "acknowledged"):
                entry["status"] = "resolved"
                entry["resolved_at"] = now
                entry["resolved_by"] = by
                updated = True
                break
        if updated:
            data["summary"] = compute_summary([FeedbackEntry(**e) for e in data["feedbacks"]])
            _write_planner_feedback_unlocked(project_root, data)
        return updated


def dismiss_feedback(project_root: str, feedback_id: str, by: str = "architect") -> bool:
    """Transition feedback to dismissed status. Returns True if found and updated."""
    lock = _lock_path(project_root)
    with FileLock(lock, timeout=10.0):
        data = read_planner_feedback_unlocked(project_root)
        updated = False
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for entry in data.get("feedbacks", []):
            if entry["feedback_id"] == feedback_id and entry["status"] in ("open", "acknowledged"):
                entry["status"] = "dismissed"
                entry["dismissed_at"] = now
                entry["dismissed_by"] = by
                updated = True
                break
        if updated:
            data["summary"] = compute_summary([FeedbackEntry(**e) for e in data["feedbacks"]])
            _write_planner_feedback_unlocked(project_root, data)
        return updated


def prune_resolved_feedback(project_root: str) -> int:
    """Remove resolved/dismissed entries. Returns count removed."""
    lock = _lock_path(project_root)
    with FileLock(lock, timeout=10.0):
        data = read_planner_feedback_unlocked(project_root)
        original = data.get("feedbacks", [])
        kept = [e for e in original if e["status"] not in ("resolved", "dismissed")]
        removed = len(original) - len(kept)
        if removed > 0:
            data["feedbacks"] = kept
            data["summary"] = compute_summary([FeedbackEntry(**e) for e in kept])
            _write_planner_feedback_unlocked(project_root, data)
        return removed


def _empty_schema(project_root: str) -> Dict[str, Any]:
    return {
        "schema": "planner-feedback-v1",
        "version": 1,
        "owner": "rdd-planner",
        "branch": "main",
        "worktree_root": project_root,
        "codebase_commit": "",
        "arch_handoff_revision": 0,
        "planner_state_last_sync_at": "",
        "feedbacks": [],
        "summary": {
            "open_critical": 0, "open_warning": 0, "open_info": 0,
            "acknowledged": 0, "resolved": 0, "dismissed": 0,
        },
    }


def _current_codebase_commit(project_root: str) -> str:
    """Return git HEAD commit hash, or empty string if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return ""


def _current_arch_handoff_revision(project_root: str) -> int:
    """Read arch_handoff_revision from .arch-handoff.json (0 if absent)."""
    path = os.path.join(project_root, ".rddf", "state", ".arch-handoff.json")
    if not os.path.exists(path):
        return 0
    try:
        with open(path) as f:
            data = json.load(f)
        return int(data.get("arch_complete_revision", 0))
    except (json.JSONDecodeError, OSError, ValueError):
        return 0


def _current_planner_state_revision(project_root: str) -> int:
    """Read state_revision from .planner-state.json (0 if absent or legacy)."""
    path = os.path.join(project_root, ".rddf", "state", ".planner-state.json")
    if not os.path.exists(path):
        return 0
    try:
        with open(path) as f:
            data = json.load(f)
        return int(data.get("state_revision", 0))
    except (json.JSONDecodeError, OSError, ValueError):
        return 0


def _next_feedback_id(date_prefix: str, prior_entries: List[Dict[str, Any]]) -> str:
    """Allocate next feedback_id of form pf-YYYYMMDD-NNN where NNN = max(prior same-date)+1.

    Defensive: skips malformed feedback_ids (missing -NNN suffix,
    non-numeric suffix, missing key) without crashing. Logs skipped IDs
    at WARNING level for audit.
    """
    prefix = f"pf-{date_prefix}-"
    max_n = 0
    skipped: List[str] = []
    for e in prior_entries:
        fid = e.get("feedback_id")
        if not isinstance(fid, str) or fid.count("-") != 2:
            skipped.append(repr(fid) if fid is not None else "<missing>")
            continue
        if not fid.startswith(prefix):
            continue
        try:
            n = int(fid.rsplit("-", 1)[1])
            max_n = max(max_n, n)
        except (ValueError, IndexError):
            skipped.append(fid)
            continue
    if skipped:
        import logging
        logging.getLogger(__name__).warning(
            "Skipped %d malformed feedback_ids in counter scan: %s",
            len(skipped),
            skipped[:5],
        )
    return f"{prefix}{max_n + 1:03d}"


def _scan_improvements(project_root: str) -> List[Dict[str, str]]:
    """Parse .rddf/improvements/*.md frontmatter → list of {name, priority, theme_ref}."""
    improvements_dir = os.path.join(project_root, ".rddf", "improvements")
    if not os.path.isdir(improvements_dir):
        return []
    results = []
    for fname in sorted(os.listdir(improvements_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(improvements_dir, fname)
        try:
            with open(fpath) as f:
                content = f.read()
        except OSError:
            continue
        m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not m:
            continue
        fm = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
        results.append({
            "name": fm.get("name", fname[:-3]),
            "priority": fm.get("priority", "P3"),
            "theme_ref": fm.get("theme_ref", ""),
        })
    return results


def compute_planner_feedback(
    project_root: str,
    *,
    codebase_commit: Optional[str] = None,
    force_recompute: bool = False,
) -> Dict[str, Any]:
    """Scan improvements + ADR + roadmap → emit persistent review tasks.

    Idempotent: same input produces same fingerprint. New entries merge with
    existing open/acknowledged entries; resolved/dismissed entries preserved.

    Stale determination (2-revision):
        is_stale = (prior.arch_handoff_revision != current) OR
                   (prior.state_revision != current)

    codebase_commit is stored in computed_from as informational metadata
    (not used for stale trigger — eliminates Stage 3 doc-only-commit noise).
    """
    if codebase_commit is None:
        codebase_commit = _current_codebase_commit(project_root)

    prior = read_planner_feedback(project_root)
    prior_entries = {e["fingerprint"]: e for e in prior.get("feedbacks", [])}
    arch_handoff_rev = _current_arch_handoff_revision(project_root)
    state_rev = _current_planner_state_revision(project_root)

    new_feedbacks: List[FeedbackEntry] = []
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    date_prefix = now_iso[:10].replace("-", "")
    counter = 1

    improvements = _scan_improvements(project_root)
    for imp in improvements:
        if not imp["theme_ref"]:
            fingerprint = compute_fingerprint(
                kind="unmapped_proposal",
                proposal=imp["name"],
                theme="",
                related_adr_ids=[],
                reason="missing_theme_ref",
            )
            severity = "critical" if imp["priority"] in ("P0", "P1") else "warning"
            feedback_id = f"pf-{date_prefix}-{counter:03d}"
            counter += 1
            new_feedbacks.append(FeedbackEntry(
                feedback_id=feedback_id,
                kind="unmapped_proposal",
                severity=severity,
                status="open",
                fingerprint=fingerprint,
                proposal=imp["name"],
                theme="",
                related_adr_ids=[],
                message=f"proposal '{imp['name']}' ({imp['priority']}) lacks theme_ref",
                suggested_action="add theme_ref to frontmatter or add matching Phase Skeleton theme",
                created_at=now_iso,
                last_seen_at=now_iso,
                acknowledged_at=None,
                resolved_at=None,
                resolved_by=None,
                dismissed_at=None,
                dismissed_by=None,
                computed_from={
                    "state_revision": state_rev,
                    "arch_handoff_revision": arch_handoff_rev,
                    "codebase_commit": codebase_commit,
                },
            ))

    merged: List[Dict[str, Any]] = []
    new_fps = {f.fingerprint for f in new_feedbacks}
    prior_feedbacks_list = prior.get("feedbacks", [])
    for f in new_feedbacks:
        as_dict = asdict(f)
        prior_match = prior_entries.get(f.fingerprint)
        if prior_match:
            as_dict["feedback_id"] = prior_match.get("feedback_id", as_dict["feedback_id"])
            as_dict["created_at"] = prior_match["created_at"]
            as_dict["last_seen_at"] = prior_match.get("last_seen_at", as_dict["last_seen_at"])
            as_dict["status"] = prior_match["status"] if prior_match["status"] != "resolved" else "open"
            as_dict["acknowledged_at"] = prior_match.get("acknowledged_at")
            as_dict["resolved_at"] = prior_match.get("resolved_at")
            as_dict["resolved_by"] = prior_match.get("resolved_by")
            as_dict["dismissed_at"] = prior_match.get("dismissed_at")
            as_dict["dismissed_by"] = prior_match.get("dismissed_by")
            prior_cf = prior_match.get("computed_from", {})
            prior_arch_rev = int(prior_cf.get("arch_handoff_revision", 0))
            prior_state_rev = int(prior_cf.get("state_revision", 0))
            as_dict["stale"] = (
                prior_arch_rev != arch_handoff_rev
                or prior_state_rev != state_rev
            )
        else:
            as_dict["feedback_id"] = _next_feedback_id(date_prefix, prior_feedbacks_list)
            prior_feedbacks_list = prior_feedbacks_list + [as_dict]
        merged.append(as_dict)

    for fp, prior_e in prior_entries.items():
        if fp not in new_fps and prior_e.get("status") in ("resolved", "dismissed"):
            merged.append(prior_e)

    summary_entries: List[FeedbackEntry] = []
    for e in merged:
        if e.get("status") == "stale_only":
            continue
        try:
            summary_entries.append(FeedbackEntry(**e))
        except (TypeError, ValueError):
            continue
    summary = compute_summary(summary_entries)

    return {
        "schema": "planner-feedback-v1",
        "version": 1,
        "owner": "rdd-planner",
        "branch": "main",
        "worktree_root": project_root,
        "codebase_commit": codebase_commit,
        "arch_handoff_revision": arch_handoff_rev,
        "state_revision": state_rev,
        "planner_state_last_sync_at": now_iso,
        "feedbacks": merged,
        "summary": summary,
    }