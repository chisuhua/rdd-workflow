"""Skill-layer Python wrapper for project_root resolution.

Mirrors the bash helper at skills/_lib/orchestrator_entry.sh::_resolve_project_root
(per add-skill-layer-resolve-project-root-helper). Delegates the canonical
implementation to _lib.cli.__main__.resolve_project_root (per ADR-0033,
submodule-aware git toplevel probe) -- no logic duplication.

Resolution order:
  1. RDDF_PROJECT_ROOT env var (override for tests + caller injection)
  2. _lib.cli.__main__.resolve_project_root() (submodule-aware git probe)
  3. os.getcwd() (fallback when not in a git repo)
"""
from __future__ import annotations

import os


def resolve_project_root() -> str:
    """Return the project root for skill scripts.

    See module docstring for the resolution order. Symmetric with the bash
    helper `_resolve_project_root` in skills/_lib/orchestrator_entry.sh.
    """
    return (
        os.environ.get("RDDF_PROJECT_ROOT")
        or _delegate_to_cli_main_resolver()
        or os.getcwd()
    )


def _delegate_to_cli_main_resolver() -> str:
    """Lazy-import the dispatcher resolver to avoid import-time cycles.

    Importing `_lib.cli.__main__` at module load would trigger __main__'s own
    `from skills._lib.cli import list_commands, route` (per fix-33-handlers
    PEP 562 __getattr__); deferring to call-time avoids any circular risk.
    """
    from _lib.cli.__main__ import resolve_project_root as _impl
    return _impl()
