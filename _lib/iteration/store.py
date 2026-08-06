"""Iteration state - CRUD, mutations, and queries.

Extracted from ``skills/_lib/iteration.py`` (v2.0.8 split). This module
holds the in-memory and on-disk data operations:

  * ``load`` / ``save`` - JSON file IO with schema validation,
    file locking (via ``core.lock.FileLock``), atomic writes
    (via ``core.atomic_write.atomic_write_json``), and merge-on-save
    to prevent lost updates between concurrent writers.
  * ``create_empty`` / ``add_or_update_change`` / ``set_status`` /
    ``set_tasks_done`` / ``set_deps_info`` / ``mark_archived`` /
    ``remove_change`` / ``set_current_phase`` - mutation helpers that
    return new dicts (do not mutate in place).
  * ``get_change`` / ``list_active`` / ``list_archived`` /
    ``list_planned`` / ``list_ready_for_fill`` / ``list_ready_for_ship`` /
    ``list_blocked`` / ``get_unblocked_planned`` - queries.
  * ``derive_feature_name`` / ``list_feature_groups`` /
    ``feature_progress`` - feature grouping helpers used by the
    ``feature`` skill and ``status`` Mode E rendering.

All public names here are re-exported from ``skills._lib.iteration``
(the package ``__init__.py``), so existing
``from skills._lib.iteration import load, save`` imports continue to
work unchanged.

A subtle but important compatibility note: ``test_iteration_concurrency``
mutates ``it_mod._LOCK_TIMEOUT`` at runtime to make the lock-timeout
test fast. To preserve that behavior, ``save()`` looks up
``_LOCK_TIMEOUT`` via ``globals()`` at call time rather than capturing
the value at module load. The module-level ``_LOCK_TIMEOUT`` variable
is the single source of truth and can be patched by tests.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import re
from typing import Any, Optional

import jsonschema

from skills._lib.core.lock import FileLock, LockTimeout
from skills._lib.iteration.schema import (
    _BLOCKING_STATUSES,
    _DEFAULT_PHASE,
    _UNSET,
    _VALID_STATUSES,
    _validate,
)

logger = logging.getLogger(__name__)

# Lock timeout for iteration.json writes. Short enough that a hung
# concurrent writer doesn't block the user; long enough that normal
# load->mutate->save sequences always complete.
#
# Patched by tests (test_iteration_concurrency.test_lock_timeout_raises_lock_timeout)
# to a small value. save() looks this up via globals() at call time so
# patches take effect without needing to re-import.
_LOCK_TIMEOUT = 5.0


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string with timezone."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _atomic_write(path: str, data: dict) -> None:
    """Write data to path atomically (write to .tmp, fsync, rename)."""
    # v2.0.3: delegate to shared atomic_write helper (Wave 3.1).
    from skills._lib.core.atomic_write import atomic_write_json
    atomic_write_json(path, data)


def _read_unlocked_verbose(path: str) -> tuple[Optional[dict], Optional[str]]:
    """Read iteration.json without acquiring the lock, returning error info.

    Like ``_read_unlocked`` but distinguishes missing from invalid by
    returning a ``(data, error_message)`` tuple:

      - File missing: ``(None, None)``
      - ``JSONDecodeError`` or ``OSError``: ``(None, "invalid JSON: <e>")``
      - ``jsonschema.ValidationError``: ``(None, "schema validation failed
        at <path>: <message>")``
      - Success: ``(data, None)``

    Used by CLI layers (``status_cmd.py``, ``feature_cli.py``) that
    need to surface corrupt-file diagnostics to users. The error
    message is safe to print: no paths, secrets, or PII.

    Read-only: does NOT write a ``.corrupt.<ts>`` backup (unlike
    :func:`load`). The read-only contract is enforced by the
    ``state_reader`` module docstring (no file writes, no lock).

    Created: fix-rddf-status-corrupt-message (P1, 2026-08-05).
    """
    if not os.path.isfile(path):
        return (None, None)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return (None, f"invalid JSON: {exc}")
    data = _migrate_to_current(data)
    # Direct validation to capture the first error's full path. Can't
    # use _validate() because it re-raises with only the message
    # string, discarding absolute_path.
    from skills._lib.iteration.schema import _load_registry, _load_schema
    schema = _load_schema()
    registry = _load_registry()
    validator = jsonschema.Draft7Validator(schema, registry=registry)
    errors = list(validator.iter_errors(data))
    if errors:
        first = errors[0]
        return (
            None,
            f"schema validation failed at {list(first.absolute_path)}: {first.message}",
        )
    return (data, None)


def _read_unlocked(path: str) -> Optional[dict]:
    """Read iteration.json without acquiring the lock. Used inside save().

    Returns None if file missing or invalid (same policy as load()).

    Thin wrapper around :func:`_read_unlocked_verbose` that discards
    the error message. Preserves byte-level behavior for existing
    callers (``save`` and others that only care about success/failure).
    """
    data, _ = _read_unlocked_verbose(path)
    return data


def _backup_corrupt_file(path: str, reason: str = "") -> Optional[str]:
    """Copy a corrupt iteration.json aside so the user can recover it.

    The backup path is `iteration.json.corrupt.<timestamp>` in the same
    directory. A sidecar file `iteration.json.corrupt.<timestamp>.reason.txt`
    is also written containing the error context (the ``reason`` arg)
    so AI agents and users can diagnose the corruption without diffing
    the corrupt JSON against the schema. If the timestamp already exists
    (rare, requires two corruptions in the same microsecond on the same
    machine), append a counter suffix. Returns the backup path, or None
    on failure.

    Failure modes are silent: if the backup can't be created (no disk
    space, permission denied), we proceed with returning empty state
    rather than blocking the caller. The backup is best-effort.

    Created: rddf-iteration-strict-schema (P1, 2026-08-05) — added
    the .reason.txt sidecar to address the "AI 写错字段静默触发备份"
    gap. The sidecar is written via a best-effort fallback so a
    permission error on the sidecar does not roll back the main backup.
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
    except OSError as e:
        logger.error("failed to back up corrupt iteration.json %s: %s", path, e)
        return None

    if reason:
        reason_path = candidate + ".reason.txt"
        try:
            with open(reason_path, "w", encoding="utf-8") as f:
                f.write(f"path: {path}\n")
                f.write(f"backup: {candidate}\n")
                f.write(f"timestamp: {ts}\n")
                f.write(f"reason: {reason}\n")
        except OSError as e:
            logger.warning("failed to write .reason.txt sidecar %s: %s",
                           reason_path, e)
    return candidate


def _merge_by_name(existing: dict, incoming: dict) -> dict:
    """Merge two iteration states by change name. Incoming wins per-name.

    Used inside save() to merge caller's data with whatever was on disk
    when we acquired the lock. Without this, concurrent writers that
    both did load->mutate->save would overwrite each other's changes.

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
        "version": 5,
        "updated_at": _now_iso(),
        "current_phase": current_phase,
        "changes": [],
    }


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------

def _migrate_v3_to_v4(data: dict) -> dict:
    """Migrate a v3 iteration state to v4 in-place.

    v4 adds `manual_deps` and `manual_blocks` mirror fields to each
    change entry. Existing v3 entries lack these fields; we set them
    to None (meaning "no deps run yet" per the schema description).

    This is a one-way migration: the version field is bumped to 4 so
    subsequent loads skip this function. The migrated data is NOT
    persisted by load() - callers that mutate-and-save will persist
    the migrated form; read-only callers leave the file untouched.
    """
    if data.get("version") != 3:
        return data
    data = dict(data)
    data["version"] = 4
    migrated_changes = []
    for c in data.get("changes", []):
        c = dict(c)
        if "manual_deps" not in c:
            c["manual_deps"] = None
        if "manual_blocks" not in c:
            c["manual_blocks"] = None
        migrated_changes.append(c)
    data["changes"] = migrated_changes
    return data


def _migrate_v4_to_v5(data: dict) -> dict:
    """Migrate a v4 iteration state to v5 in-place.

    v5 adds `l2_violation_count_after` and `l2_violation_kind` per-change
    fields. Existing v4 entries lack these fields; we set them to None
    (meaning 'L2 count was not recorded at archive time').

    Same idempotent / non-persisting contract as _migrate_v3_to_v4.
    """
    if data.get("version") != 4:
        return data
    data = dict(data)
    data["version"] = 5
    migrated_changes = []
    for c in data.get("changes", []):
        c = dict(c)
        c.setdefault("l2_violation_count_after", None)
        c.setdefault("l2_violation_kind", None)
        migrated_changes.append(c)
    data["changes"] = migrated_changes
    return data


def _migrate_to_current(data: dict) -> dict:
    """Walk a versioned iteration state forward to the current schema.

    Returns the migrated dict (a shallow copy if any step ran, or the
    input unchanged if already at the current version). Each step is
    idempotent: if the version field already matches, the function is
    a no-op. Shared by load() and _read_unlocked_verbose() so both
    write-side and read-side paths surface the same shape.
    """
    if isinstance(data, dict) and data.get("version") == 3:
        data = _migrate_v3_to_v4(data)
    if isinstance(data, dict) and data.get("version") == 4:
        data = _migrate_v4_to_v5(data)
    return data


def load(project_root: str) -> dict:
    """Load iteration state from disk.

    Behavior:
      - File missing -> return empty state (do not create file).
      - File present + valid JSON + schema-valid -> return parsed data.
      - File present + valid JSON but version=3 -> migrate to v4 in
        memory (add manual_deps/manual_blocks=None to each change),
        validate, return. File is NOT rewritten; read-only callers
        leave the v3 file on disk. Next save() persists the v4 form.
      - File present + invalid JSON -> log error, copy file aside to
        `iteration.json.corrupt.<timestamp>`, return empty state.
      - File present + valid JSON but schema-invalid (other than
        version=3) -> same: log error, back up the file, return
        empty state.

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
        _backup_corrupt_file(path, f"invalid JSON: {e}")
        return create_empty()
    data = _migrate_to_current(data)
    try:
        _validate(data)
    except jsonschema.ValidationError as e:
        logger.error(
            "iteration.json at %s fails schema validation: %s; backing up and returning empty",
            path, e.message,
        )
        _backup_corrupt_file(path, f"schema validation failed: {e.message}")
        return create_empty()
    return data


def save(project_root: str, data: dict) -> None:
    """Save iteration state atomically with merge-on-save.

    Updates `updated_at` and validates schema before write. Inside the
    lock, re-reads the file and merges with caller's data by change
    name (caller wins per-name). This prevents the lost-update bug:
    without merging, two hooks doing load->mutate->save concurrently
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
    # Read _LOCK_TIMEOUT via globals() at call time so test patches to
    # the module attribute take effect without re-import.
    with FileLock(lock_path, timeout=globals()["_LOCK_TIMEOUT"]):
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


def get_unblocked_planned(project_root: str) -> list[dict]:
    """[Post-archive hook] Return planned changes whose blockers are resolved.

    Called by guide-ship Phase 3 after archive completes. Returns skeleton
    (planned) changes whose blocker has transitioned to completed/archived,
    making them candidates for fill.

    More restrictive than list_ready_for_fill: only considers explicitly
    resolved blockers (status in {"completed", "archived"}), not missing
    or unlisted blockers.

    Args:
        project_root: Path to project root with .rddf/state/iteration.json
    Returns:
        List of change dicts with at minimum name, status, blocker fields.
    """
    data = load(project_root)
    unblocked: list[dict] = []
    for c in data.get("changes", []):
        if c.get("status") != "planned":
            continue
        blocker_name = c.get("blocker")
        if not blocker_name:
            unblocked.append(c)
            continue
        blocker = get_change(data, blocker_name)
        if blocker and blocker.get("status") in ("completed", "archived"):
            unblocked.append(c)
    return unblocked


# ---------------------------------------------------------------------------
# Feature grouping - derived from change name prefix (no schema change)
# Convention: feature-<name>-<sub>, e.g. feature-stream-core -> feature-stream
# Regex: single-word feature names only (no hyphens in the feature part).
# Non-conforming changes (no feature- prefix) become single-change features.
# ---------------------------------------------------------------------------

_FEATURE_PREFIX_RE = re.compile(r"^(feature-[a-z0-9]+)(-[a-z0-9-]+)?$")


def derive_feature_name(name: str, data: Optional[dict] = None) -> str:
    """Derive the parent feature name for a change.

    Resolution order:
    1. ``parent_feature`` field in iteration.json (explicit registration)
    2. Name-prefix convention: ``feature-<name>-<sub>`` -> ``feature-<name>``
    3. Fallback: return the change name as-is (single-change feature)

    feature-stream-core -> feature-stream
    feature-stream      -> feature-stream  (single sub-change)
    debt-cleanup-foo    -> debt-cleanup-foo (no feature- prefix - self-group)
    """
    # 1. Check explicit parent_feature field
    if data is not None:
        change = get_change(data, name)
        if change is not None:
            pf = change.get("parent_feature")
            if pf:
                return pf
    # 2. Name-prefix convention
    m = _FEATURE_PREFIX_RE.match(name)
    return m.group(1) if m else name


def list_feature_groups(data: dict) -> dict[str, list[dict]]:
    """Group changes by derived feature name.

    Returns a dict keyed by feature name, values are lists of change dicts.
    Changes without a ``feature-`` prefix each become their own single-entry
    group (keyed by their own name).
    """
    groups: dict[str, list[dict]] = {}
    for c in data.get("changes", []):
        feature = derive_feature_name(c["name"], data)
        groups.setdefault(feature, []).append(c)
    return groups


def feature_progress(data: dict) -> dict[str, tuple[int, int]]:
    """Return per-feature completion counts (archived, total).

    A sub-change counts as "archived" only when its status is ``archived``
    (code merged into default branch).  ``completed`` is a transitional
    state (tasks done but not yet merged) and does NOT count as done here.
    """
    out: dict[str, tuple[int, int]] = {}
    for feature, changes in list_feature_groups(data).items():
        total = len(changes)
        done = sum(1 for c in changes if c.get("status") == "archived")
        out[feature] = (done, total)
    return out


# ---------------------------------------------------------------------------
# Mutations (return new data dict, do not mutate in place - easier to test)
# ---------------------------------------------------------------------------

def add_or_update_change(data: dict, **fields: Any) -> dict:
    """Add a new change entry or update an existing one. Preserves added_at.

    Required fields in `fields`: name, status.
    Optional: phase, category, priority, worktree_path, plan_path,
              tasks_done, tasks_total, blocker, parallel_group,
              conflicts, last_deps_at, archived_at, manual_deps,
              manual_blocks.

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
    manual_deps: Any = _UNSET,
    manual_blocks: Any = _UNSET,
) -> dict:
    """Update blocker/parallel_group/conflicts from a deps run. Records last_deps_at.

    Uses sentinel values so callers can pass `blocker=None` to explicitly
    clear a previously-recorded blocker. Arguments that are not passed
    (i.e. still equal to _UNSET) are left untouched.

    `manual_deps` and `manual_blocks` carry human-authored dependency
    overrides from roadmap-meta.yaml. They are mirror fields: `manual_deps`
    is the list of changes this one depends on; `manual_blocks` is the
    reverse-dependency list of changes that must wait for this one.
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
    if manual_deps is not _UNSET:
        fields["manual_deps"] = list(manual_deps) if manual_deps is not None else None
    if manual_blocks is not _UNSET:
        fields["manual_blocks"] = list(manual_blocks) if manual_blocks is not None else None
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
    """Remove a change entry entirely. Use sparingly - mark_archived is preferred.

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
