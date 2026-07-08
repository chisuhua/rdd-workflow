"""Iteration state — persistent view of the current sprint.

Stored as JSON at `.rddf/state/iteration.json`. The file is a sibling of
`roadmap-state.json` and `plan-handoff.json` in the gitignored `.rddf/state/`
directory. Unlike `state_vector.json` (which is the Loop engine's
checksummed, locked authoritative state), iteration.json is a
**view-oriented** file: it is a denormalized projection of multiple
sources (propose hooks, deps output, execute progress, archive) into a
single table that `status` Mode E and `roadmap.md` AUTO-SPRINT renderers
can read.

Design choices:
- No file lock: iteration.json is written by long-running skills
  (propose, execute, archive) that are themselves the only writers for
  their own change names. Concurrent writers would target different
  entries in the `changes` array, and the worst case is a lost write
  on the same entry. This is acceptable because (a) contention is
  human-paced, not loop-paced, and (b) the source-of-truth files
  (tasks.md, deps-output.md, openspec status) are unaffected.
- No checksum: lost writes are recoverable by re-running the hook
  (e.g. `skill_use("status", "iteration", "refresh")`).
- Schema-validated on load (catches corruption early) but not on
  every write (would slow propose hook). Schema lives at
  `schemas/iteration_schema.json`.
- Atomic write: write to `.tmp` then rename.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import jsonschema

from skills._lib.lock import FileLock, LockTimeout

logger = logging.getLogger(__name__)

SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__), "schemas", "iteration_schema.json"
)
_DEFAULT_PHASE = "default"
_VALID_STATUSES = ("planned", "proposed", "in_worktree", "review", "completed", "archived")
# Statuses that block a dependent planned change from being filled.
# A planned change's blocker must be in one of these statuses to count as
# "still blocking". When a blocker transitions out (e.g. to archived), the
# dependent becomes "unblocked" and ready for fill.
_BLOCKING_STATUSES = ("planned", "in_worktree", "review")

# Sentinel for distinguishing "argument not passed" from "argument passed
# as None". Used by set_deps_info so callers can explicitly clear a
# field (blocker=None) without affecting it.
_UNSET: Any = object()

# Lock timeout for iteration.json writes. Short enough that a hung
# concurrent writer doesn't block the user; long enough that normal
# load→mutate→save sequences always complete.
_LOCK_TIMEOUT = 5.0


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string with timezone."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _load_schema() -> dict:
    """Load the JSON Schema (cached on first call)."""
    if not os.path.isfile(SCHEMA_PATH):
        raise FileNotFoundError(
            f"iteration schema not found at {SCHEMA_PATH}; "
            f"the iteration.py module requires it for validation"
        )
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def _validate(data: dict) -> None:
    """Validate iteration data against the schema. Raises jsonschema.ValidationError on failure."""
    schema = _load_schema()
    jsonschema.validate(data, schema)


def _atomic_write(path: str, data: dict) -> None:
    """Write data to path atomically (write to .tmp, fsync, rename)."""
    target_dir = os.path.dirname(path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def _read_unlocked(path: str) -> Optional[dict]:
    """Read iteration.json without acquiring the lock. Used inside save().

    Returns None if file missing or invalid (same policy as load()).
    """
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    try:
        _validate(data)
    except jsonschema.ValidationError:
        return None
    return data


def _backup_corrupt_file(path: str) -> Optional[str]:
    """Copy a corrupt iteration.json aside so the user can recover it.

    The backup path is `iteration.json.corrupt.<timestamp>` in the same
    directory. If the timestamp already exists (rare, requires two
    corruptions in the same microsecond on the same machine), append
    a counter suffix. Returns the backup path, or None on failure.

    Failure modes are silent: if the backup can't be created (no disk
    space, permission denied), we proceed with returning empty state
    rather than blocking the caller. The backup is best-effort.
    """
    if not os.path.isfile(path):
        return None
    base, _ = os.path.splitext(path)
    parent = os.path.dirname(path)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    candidate = os.path.join(parent, f"{os.path.basename(base)}.corrupt.{ts}")
    counter = 0
    while os.path.exists(candidate):
        counter += 1
        candidate = os.path.join(
            parent, f"{os.path.basename(base)}.corrupt.{ts}.{counter}"
        )
        if counter > 100:
            logger.warning(
                "could not create unique backup path for %s after 100 attempts",
                path,
            )
            return None
    try:
        import shutil
        shutil.copy2(path, candidate)
        logger.warning(
            "backed up corrupt iteration.json: %s -> %s", path, candidate,
        )
        return candidate
    except OSError as e:
        logger.error("failed to back up corrupt iteration.json %s: %s", path, e)
        return None


def _merge_by_name(existing: dict, incoming: dict) -> dict:
    """Merge two iteration states by change name. Incoming wins per-name.

    Used inside save() to merge caller's data with whatever was on disk
    when we acquired the lock. Without this, concurrent writers that
    both did load→mutate→save would overwrite each other's changes.

    Non-changes fields (current_phase, updated_at) come from incoming
    (the caller is the authoritative source for these).
    """
    existing_by_name = {c.get("name"): c for c in existing.get("changes", [])}
    for new_c in incoming.get("changes", []):
        existing_by_name[new_c.get("name")] = new_c
    merged = dict(incoming)
    merged["changes"] = list(existing_by_name.values())
    return merged


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def create_empty(current_phase: str = _DEFAULT_PHASE) -> dict:
    """Return a fresh empty iteration state. Useful for `skill_use("status", "iteration", "init")`."""
    return {
        "version": 3,
        "updated_at": _now_iso(),
        "current_phase": current_phase,
        "changes": [],
    }


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------

def load(project_root: str) -> dict:
    """Load iteration state from disk.

    Behavior:
      - File missing → return empty state (do not create file).
      - File present + valid JSON + schema-valid → return parsed data.
      - File present + invalid JSON → log error, copy file aside to
        `iteration.json.corrupt.<timestamp>`, return empty state.
      - File present + valid JSON but schema-invalid → same: log error,
        back up the file, return empty state.

    The "return empty on error" policy is intentional: hooks call
    `load()` to read state, mutate, then `save()`. A missing or
    corrupted file is treated as "no changes tracked yet", which is
    the right initial state for hooks that may fire before any
    iteration is established. The backup gives the user a recovery
    path (they can inspect or restore the corrupt file manually)
    instead of silently overwriting history on the next save.
    """
    path = os.path.join(project_root, ".rddf", "state", "iteration.json")
    if not os.path.isfile(path):
        logger.debug("iteration.json not found at %s; returning empty state", path)
        return create_empty()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("iteration.json at %s is unreadable: %s; backing up and returning empty", path, e)
        _backup_corrupt_file(path)
        return create_empty()
    try:
        _validate(data)
    except jsonschema.ValidationError as e:
        logger.error(
            "iteration.json at %s fails schema validation: %s; backing up and returning empty",
            path, e.message,
        )
        _backup_corrupt_file(path)
        return create_empty()
    return data


def save(project_root: str, data: dict) -> None:
    """Save iteration state atomically with merge-on-save.

    Updates `updated_at` and validates schema before write. Inside the
    lock, re-reads the file and merges with caller's data by change
    name (caller wins per-name). This prevents the lost-update bug:
    without merging, two hooks doing load→mutate→save concurrently
    would each see stale state and overwrite each other's changes.

    Semantics: "I want to ensure THESE changes are persisted; preserve
    any unrelated changes made by other writers since I loaded."

    Raises jsonschema.ValidationError on schema failure.
    Raises OSError on I/O failure.
    Raises skills._lib.lock.LockTimeout if another writer holds the lock
    beyond _LOCK_TIMEOUT (callers should catch and log).
    """
    data = dict(data)  # shallow copy so we don't mutate caller's dict
    data["updated_at"] = _now_iso()
    _validate(data)
    path = os.path.join(project_root, ".rddf", "state", "iteration.json")
    lock_path = path + ".lock"
    with FileLock(lock_path, timeout=_LOCK_TIMEOUT):
        existing = _read_unlocked(path)
        if existing is not None:
            data = _merge_by_name(existing, data)
            data["updated_at"] = _now_iso()  # refresh after merge
            _validate(data)  # re-validate after merge
        _atomic_write(path, data)
    logger.debug("iteration.json saved to %s (%d changes)", path, len(data.get("changes", [])))


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_change(data: dict, name: str) -> Optional[dict]:
    """Return the change entry with the given name, or None if not present."""
    for entry in data.get("changes", []):
        if entry.get("name") == name:
            return entry
    return None


def list_active(data: dict) -> list[dict]:
    """Return changes in {proposed, in_worktree, completed} (excluding archived)."""
    return [
        c for c in data.get("changes", [])
        if c.get("status") in ("proposed", "in_worktree", "completed")
    ]


def list_archived(data: dict) -> list[dict]:
    """Return archived changes (most recent first by archived_at)."""
    archived = [c for c in data.get("changes", []) if c.get("status") == "archived"]
    archived.sort(
        key=lambda c: c.get("archived_at") or "",
        reverse=True,
    )
    return archived


def list_planned(data: dict) -> list[dict]:
    """[Queue 2] Return changes in `planned` status (skeleton, not yet filled)."""
    return [c for c in data.get("changes", []) if c.get("status") == "planned"]


def list_ready_for_fill(data: dict) -> list[dict]:
    """[Queue 2 衍生] Return planned changes whose blocker is cleared (None or
    in a non-blocking status: completed/archived).

    A change is fillable when:
    - status is `planned`, AND
    - blocker is None, OR
    - blocker is set but the blocker entry does not exist, OR
    - blocker is set and the blocker entry's status is NOT in _BLOCKING_STATUSES.
    """
    out: list[dict] = []
    for c in data.get("changes", []):
        if c.get("status") != "planned":
            continue
        blocker = c.get("blocker")
        if not blocker:
            out.append(c)
            continue
        blocker_entry = get_change(data, blocker)
        if blocker_entry is None or blocker_entry.get("status") not in _BLOCKING_STATUSES:
            out.append(c)
    return out


def list_ready_for_ship(data: dict) -> list[dict]:
    """[Queue 4] Return proposed changes whose blocker is cleared.

    Used by guide-plan-done gate 0. A change is shippable when:
    - status is `proposed`, AND
    - blocker is None, OR
    - blocker is set but the blocker entry does not exist, OR
    - blocker is set and the blocker entry's status is NOT in _BLOCKING_STATUSES.
    """
    out: list[dict] = []
    for c in data.get("changes", []):
        if c.get("status") != "proposed":
            continue
        blocker = c.get("blocker")
        if not blocker:
            out.append(c)
            continue
        blocker_entry = get_change(data, blocker)
        if blocker_entry is None or blocker_entry.get("status") not in _BLOCKING_STATUSES:
            out.append(c)
    return out


def list_blocked(data: dict) -> list[dict]:
    """[Queue 5] Return planned/proposed changes with an active blocker.

    A change is blocked when:
    - status is `planned` or `proposed`, AND
    - blocker is set, AND
    - the blocker entry exists with status in _BLOCKING_STATUSES.
    """
    out: list[dict] = []
    for c in data.get("changes", []):
        if c.get("status") not in ("planned", "proposed"):
            continue
        blocker = c.get("blocker")
        if not blocker:
            continue
        blocker_entry = get_change(data, blocker)
        if blocker_entry and blocker_entry.get("status") in _BLOCKING_STATUSES:
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# Mutations (return new data dict, do not mutate in place — easier to test)
# ---------------------------------------------------------------------------

def add_or_update_change(data: dict, **fields: Any) -> dict:
    """Add a new change entry or update an existing one. Preserves added_at.

    Required fields in `fields`: name, status.
    Optional: phase, category, priority, worktree_path, plan_path,
              tasks_done, tasks_total, blocker, parallel_group,
              conflicts, last_deps_at, archived_at.

    Returns a new data dict (caller should `save()` it).
    """
    if "name" not in fields:
        raise ValueError("add_or_update_change requires 'name'")
    if "status" not in fields:
        raise ValueError("add_or_update_change requires 'status'")
    if fields["status"] not in _VALID_STATUSES:
        raise ValueError(
            f"invalid status {fields['status']!r}; must be one of {_VALID_STATUSES}"
        )

    data = dict(data)
    data["changes"] = list(data.get("changes", []))
    existing_idx = next(
        (i for i, c in enumerate(data["changes"]) if c.get("name") == fields["name"]),
        None,
    )
    if existing_idx is not None:
        merged = dict(data["changes"][existing_idx])
        merged.update(fields)
        # Never let an update reset added_at
        if "added_at" in fields and "added_at" in data["changes"][existing_idx]:
            merged["added_at"] = data["changes"][existing_idx]["added_at"]
        data["changes"][existing_idx] = merged
    else:
        new_entry = {"added_at": _now_iso()}
        new_entry.update(fields)
        data["changes"].append(new_entry)
    return data


def set_status(data: dict, name: str, status: str) -> dict:
    """Convenience: update only the status field of a change (creates the entry if missing)."""
    if status not in _VALID_STATUSES:
        raise ValueError(
            f"invalid status {status!r}; must be one of {_VALID_STATUSES}"
        )
    return add_or_update_change(data, name=name, status=status)


def set_tasks_done(data: dict, name: str, done: int, total: Optional[int] = None) -> dict:
    """Update tasks_done (and optionally tasks_total) for a change."""
    if done < 0:
        raise ValueError("tasks_done must be >= 0")
    if total is not None and total < 0:
        raise ValueError("tasks_total must be >= 0")
    kwargs = {"name": name, "status": "in_worktree", "tasks_done": done}
    if total is not None:
        kwargs["tasks_total"] = total
    return add_or_update_change(data, **kwargs)


def set_deps_info(
    data: dict,
    name: str,
    blocker: Any = _UNSET,
    parallel_group: Any = _UNSET,
    conflicts: Any = _UNSET,
) -> dict:
    """Update blocker/parallel_group/conflicts from a deps run. Records last_deps_at.

    Uses sentinel values so callers can pass `blocker=None` to explicitly
    clear a previously-recorded blocker. Arguments that are not passed
    (i.e. still equal to _UNSET) are left untouched.
    """
    existing = get_change(data, name)
    fields: dict = {
        "name": name,
        "last_deps_at": _now_iso(),
    }
    if existing is not None:
        # Preserve status (deps doesn't change lifecycle state)
        fields["status"] = existing.get("status", "proposed")
    else:
        fields["status"] = "proposed"
    if blocker is not _UNSET:
        fields["blocker"] = blocker
    if parallel_group is not _UNSET:
        fields["parallel_group"] = parallel_group
    if conflicts is not _UNSET:
        fields["conflicts"] = list(conflicts)
    return add_or_update_change(data, **fields)


def mark_archived(data: dict, name: str) -> dict:
    """Transition a change to archived status. Sets archived_at timestamp."""
    return add_or_update_change(
        data,
        name=name,
        status="archived",
        archived_at=_now_iso(),
    )


def remove_change(data: dict, name: str) -> dict:
    """Remove a change entry entirely. Use sparingly — mark_archived is preferred.

    This is provided for hard-delete use cases (e.g. user manually
    deletes a change directory and wants iteration state to forget it).
    """
    data = dict(data)
    data["changes"] = [c for c in data.get("changes", []) if c.get("name") != name]
    return data


def set_current_phase(data: dict, phase: str) -> dict:
    """Update current_phase (e.g. when user advances the roadmap)."""
    data = dict(data)
    data["current_phase"] = phase
    return data
