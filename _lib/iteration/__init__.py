"""Iteration state - persistent view of the current sprint.

Stored as JSON at ``.rddf/state/iteration.json``. The file is a sibling of
``roadmap-state.json`` and ``plan-handoff.json`` in the gitignored
``.rddf/state/`` directory. Unlike ``state_vector.json`` (which is the
Loop engine's checksummed, locked authoritative state), iteration.json
is a **view-oriented** file: it is a denormalized projection of
multiple sources (propose hooks, deps output, execute progress,
archive) into a single table that ``status`` Mode E and
``roadmap.md`` AUTO-SPRINT renderers can read.

Design choices:
- No file lock: iteration.json is written by long-running skills
  (propose, execute, archive) that are themselves the only writers for
  their own change names. Concurrent writers would target different
  entries in the ``changes`` array, and the worst case is a lost write
  on the same entry. This is acceptable because (a) contention is
  human-paced, not loop-paced, and (b) the source-of-truth files
  (tasks.md, deps-output.md, openspec status) are unaffected.
- No checksum: lost writes are recoverable by re-running the hook
  (e.g. ``skill_use("status", "iteration", "refresh")``).
- Schema-validated on load (catches corruption early) but not on
  every write (would slow propose hook). Schema lives at
  ``schemas/iteration_schema.json``.
- Atomic write: write to ``.tmp`` then rename.

v2.0.8 split: this module was previously a single 739-line
``skills/_lib/iteration.py`` file. It has been split into a package
with three sub-modules:

  - ``schema.py`` - schema constants, validation helpers (SCHEMA_PATH,
    _VALID_STATUSES, _BLOCKING_STATUSES, _UNSET, _validate, ...)
  - ``store.py`` - CRUD + merge logic (load, save, init_iteration,
    add_or_update_change, set_deps_info, get_blocked, get_change,
    get_unblocked_planned, _atomic_write, ...)
  - ``render.py`` - CLI/status rendering (print_view)

This ``__init__.py`` re-exports the entire public API (and the
module-level constants that tests patch, such as ``_LOCK_TIMEOUT``)
so existing imports like::

    from skills._lib import iteration as it
    from skills._lib.iteration import _UNSET, SCHEMA_PATH, print_view

continue to work unchanged. The split is invisible to all consumers.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Schema layer
# ---------------------------------------------------------------------------
from skills._lib.iteration.schema import (
    _BLOCKING_STATUSES,
    _DEFAULT_PHASE,
    _UNSET,
    _VALID_STATUSES,
    _is_registered,
    _load_registry,
    _load_schema,
    _register_refs,
    _validate,
    SCHEMA_PATH,
)

# ---------------------------------------------------------------------------
# Store layer (CRUD + mutations + queries + feature grouping)
# ---------------------------------------------------------------------------
from skills._lib.iteration.store import (
    _atomic_write,
    _backup_corrupt_file,
    _LOCK_TIMEOUT,
    _merge_by_name,
    _now_iso,
    _read_unlocked,
    add_or_update_change,
    create_empty,
    derive_feature_name,
    feature_progress,
    get_change,
    get_unblocked_planned,
    list_active,
    list_archived,
    list_blocked,
    list_feature_groups,
    list_planned,
    list_ready_for_fill,
    list_ready_for_ship,
    load,
    mark_archived,
    remove_change,
    save,
    set_current_phase,
    set_deps_info,
    set_status,
    set_tasks_done,
    _FEATURE_PREFIX_RE,
)

# ---------------------------------------------------------------------------
# Render layer
# ---------------------------------------------------------------------------
from skills._lib.iteration.render import print_view

# ---------------------------------------------------------------------------
# Post-archive sync helper (fix-archive-iteration-sync, 2026-08-05)
# ---------------------------------------------------------------------------
from skills._lib.iteration import post_archive  # noqa: E402  (re-export)

# ---------------------------------------------------------------------------
# Aliases preserved for backward compatibility
# ---------------------------------------------------------------------------
#
# The original iteration.py exposed `load` / `save` as the canonical
# IO entry points. A number of historical docs and proposals referred
# to them as `load_iteration` / `write_iteration` / `init_iteration`.
# The task brief for the v2.0.8 split called these out as required
# re-exports, so we wire them up here as aliases. They are thin
# forwarders - no behavioral change.
#
# Note: `init_iteration(project_root, changes)` was not actually
# defined in the original module (only `create_empty(current_phase)`
# was). We provide an `init_iteration` helper that seeds an empty
# iteration.json (equivalent to `save(project_root, create_empty())`)
# so consumers that import the name have something usable. This is
# additive only - existing tests do not import these names, so
# behavior is unchanged.
def load_iteration(project_root: str) -> dict:
    """Backward-compat alias for :func:`load`."""
    return load(project_root)


def write_iteration(project_root: str, data: dict) -> None:
    """Backward-compat alias for :func:`save`."""
    save(project_root, data)


def init_iteration(project_root: str, changes=None) -> dict:
    """Initialize an empty iteration.json on disk.

    Equivalent to ``save(project_root, create_empty())``. ``changes``
    is accepted for forward-compat but currently ignored (the original
    module never defined this function; we provide it as a named
    entry point for consumers that referenced it in docs).
    """
    data = create_empty()
    save(project_root, data)
    return data


# Backward-compat alias for `get_blocked` referenced in task brief.
# The original module named this `list_blocked`; alias preserved so
# `from skills._lib.iteration import get_blocked` works.
get_blocked = list_blocked


__all__ = [
    # schema layer
    "SCHEMA_PATH",
    "_DEFAULT_PHASE",
    "_VALID_STATUSES",
    "_BLOCKING_STATUSES",
    "_UNSET",
    "_load_schema",
    "_load_registry",
    "_register_refs",
    "_is_registered",
    "_validate",
    # store layer - constants
    "_LOCK_TIMEOUT",
    "_FEATURE_PREFIX_RE",
    # store layer - io
    "load",
    "save",
    "create_empty",
    "_atomic_write",
    "_read_unlocked",
    "_backup_corrupt_file",
    "_merge_by_name",
    "_now_iso",
    # store layer - queries
    "get_change",
    "list_active",
    "list_archived",
    "list_planned",
    "list_ready_for_fill",
    "list_ready_for_ship",
    "list_blocked",
    "get_blocked",
    "get_unblocked_planned",
    # store layer - feature grouping
    "derive_feature_name",
    "list_feature_groups",
    "feature_progress",
    # store layer - mutations
    "add_or_update_change",
    "set_status",
    "set_tasks_done",
    "set_deps_info",
    "mark_archived",
    "remove_change",
    "set_current_phase",
    # render layer
    "print_view",
    # post-archive sync helper (fix-archive-iteration-sync)
    "post_archive",
    # backward-compat aliases
    "load_iteration",
    "write_iteration",
    "init_iteration",
]
