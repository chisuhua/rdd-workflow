"""Iteration state management (v7 cross_repo_dependencies).

Backward-compat shim re-exports from _lib.iteration for existing code.
Add cross_repo_dependencies field support for Hub-and-Spoke federation.

Per commit c3a90fe (flatten package layout), the full implementation lives
under the repo-root `_lib/iteration/` package. This shim widens __path__
to include that package AND re-exports its full public API, so
`from skills._lib.iteration import X` resolves to the same symbols as
`from _lib.iteration import X` — without this, bash subprocess invocations
(e.g. propose_change.sh, archive.sh) that import `skills._lib.iteration`
load this file instead and miss the public API
(load / save / create_empty / add_or_update_change / ...).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Union

# Path-widening: make `skills._lib.iteration` resolve to the same symbols
# as `_lib.iteration` regardless of which layout the caller uses.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_DIR)))
_FLATTEN_ITERATION = os.path.join(_REPO_ROOT, "_lib", "iteration")
if _FLATTEN_ITERATION not in __path__:
    __path__.insert(0, _FLATTEN_ITERATION)


def _load_flatten_iteration_module():
    """Load `_lib/iteration/__init__.py` directly by file path.

    A naive `from _lib import iteration` here would re-enter this shim
    itself (because `skills/` is on sys.path before the repo root in the
    feature_cli call chain), giving a partially-initialized module with
    no public API. Loading by spec sidesteps that circular import.

    The module is registered as `_lib.iteration` so the package's own
    relative imports (`from .schema import ...`) resolve correctly.
    """
    spec = importlib.util.spec_from_file_location(
        "_lib.iteration",
        os.path.join(_FLATTEN_ITERATION, "__init__.py"),
        submodule_search_locations=[_FLATTEN_ITERATION],
    )
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Cannot load flatten-layout iteration package from "
            f"{_FLATTEN_ITERATION}/__init__.py"
        )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_lib.iteration"] = mod
    spec.loader.exec_module(mod)
    return mod


_flatten_iteration = _load_flatten_iteration_module()

PathLike = Union[str, Path]


# v7 schema helpers (added in commit 02fe62f harden-archive-iteration-sync)
import json as _json

def load_iteration_v6_compat(data: dict) -> dict:
    """Migrate v6 → v7 (add cross_repo_dependencies default)."""
    data = dict(data)
    data["version"] = 7
    for change in data.get("changes", {}).values():
        change.setdefault("cross_repo_dependencies", [])
    return data


def save_iteration_v7(path: PathLike, data: dict) -> None:
    """Write iteration data in v7 format."""
    Path(path).write_text(_json.dumps(data, indent=2))


# Re-export the full public API from the flatten-layout package so that
# `from skills._lib.iteration import X` works for every X the flatten
# package exposes (load / save / create_empty / add_or_update_change / ...).
_PUBLIC_API_NAMES = [
    "SCHEMA_PATH", "_DEFAULT_PHASE", "_VALID_STATUSES", "_BLOCKING_STATUSES",
    "_UNSET", "_load_schema", "_load_registry", "_register_refs",
    "_is_registered", "_validate",
    "_LOCK_TIMEOUT", "_FEATURE_PREFIX_RE",
    "load", "save", "create_empty", "_atomic_write", "_read_unlocked",
    "_backup_corrupt_file", "_merge_by_name", "_now_iso",
    "get_change", "list_active", "list_archived", "list_planned",
    "list_ready_for_fill", "list_ready_for_ship", "list_blocked",
    "get_blocked", "get_unblocked_planned",
    "derive_feature_name", "list_feature_groups", "feature_progress",
    "add_or_update_change", "set_status", "set_tasks_done", "set_deps_info",
    "mark_archived", "remove_change", "set_current_phase",
    "print_view",
    "post_archive",
    "load_iteration", "write_iteration", "init_iteration",
]

globals().update({n: getattr(_flatten_iteration, n) for n in _PUBLIC_API_NAMES if hasattr(_flatten_iteration, n)})
