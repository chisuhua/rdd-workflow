"""Shared read-only data layer for all CLI subcommands.

This module provides 8 fine-grained functions that each read from a
specific state source (``.rddf/state/*.json``, ``proposal-suggestions.md``,
``git worktree list``, ``openspec/changes/``). All functions are strictly
read-only: they never write, backup, or mutate any file. All return
``None`` (or ``[]`` for list-returning functions) for missing or corrupt
files and never raise.

Design contract
---------------
- **Read-only**: no file is ever written, renamed, or backed up.
  This is critical for ``read_iteration`` which deliberately calls
  ``iteration.store._read_unlocked()`` rather than ``load()`` - the
  latter writes a ``.corrupt.<ts>`` backup on schema-invalid data,
  which would violate the read-only contract.
- **Never raises**: ``FileNotFoundError``, ``json.JSONDecodeError``,
  ``OSError``, and ``subprocess`` failures are all caught and surfaced
  as ``None`` (for scalar/dict readers) or ``[]`` (for list readers).
  Callers can branch on ``is None`` to distinguish "not initialized
  yet" from "empty".
- **Standard library only**: no new external dependencies.
  ``iteration.store`` is an internal module already required by the
  project (pulls in ``jsonschema`` which is already a declared dep).

Consumed by
-----------
- ``guide`` recommender (scan-state)
- ``status`` CLI subcommands (all modes)
- ``feature`` CLI subcommands
- ``guide-arch`` / ``guide-plan`` / ``guide-ship`` intake phases

Return contract per function::
    read_arch_handoff         -> dict | None
    read_plan_handoff         -> dict | None
    read_iteration            -> dict | None
    read_sessions             -> list[dict] | None
    read_roadmap_state        -> dict | None
    read_proposal_suggestions -> list[dict] | None
    list_worktrees            -> list[dict]  (empty on error, never None)
    list_change_dirs          -> list[str]   (empty on error, never None)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Optional

from skills._lib.iteration.store import _read_unlocked

logger = logging.getLogger(__name__)

# State directory relative to project root (gitignored, main repo only).
_STATE_DIR = os.path.join(".rddf", "state")


def _state_path(project_root: str, filename: str) -> str:
    """Join ``project_root / .rddf / state / filename``."""
    return os.path.join(project_root, _STATE_DIR, filename)


def read_arch_handoff(project_root: str) -> Optional[dict]:
    """Read ``.rddf/state/.arch-handoff.json``.

    Returns the parsed dict, or ``None`` if the file is missing, contains
    invalid JSON, or the top-level value is not a dict.
    """
    path = _state_path(project_root, ".arch-handoff.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def read_plan_handoff(project_root: str) -> Optional[dict]:
    """Read ``.rddf/state/.plan-handoff.json``.

    Returns the parsed dict, or ``None`` if the file is missing, contains
    invalid JSON, or the top-level value is not a dict.
    """
    path = _state_path(project_root, ".plan-handoff.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def read_iteration(project_root: str) -> Optional[dict]:
    """Read ``.rddf/state/iteration.json`` via ``_read_unlocked``.

    Deliberately uses ``iteration.store._read_unlocked`` rather than
    ``iteration.store.load``: ``load`` writes a ``.corrupt.<ts>`` backup
    file on schema-invalid data, which would violate the read-only
    contract of this module. ``_read_unlocked`` performs the same
    schema validation but returns ``None`` on any failure without
    writing anything.

    Returns the parsed and validated dict, or ``None`` if the file is
    missing, contains invalid JSON, or fails schema validation.
    """
    path = _state_path(project_root, "iteration.json")
    return _read_unlocked(path)


def read_sessions(project_root: str) -> Optional[list[dict]]:
    """Read ``.rddf/state/sessions.json`` and extract the ``sessions`` list.

    The file has structure ``{"version": 1, "sessions": [...]}``. This
    function returns only the ``sessions`` list, or ``None`` if the file
    is missing, contains invalid JSON, or the ``sessions`` field is
    absent / not a list.
    """
    path = _state_path(project_root, "sessions.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    sessions = data.get("sessions")
    if not isinstance(sessions, list):
        return None
    return sessions


def read_roadmap_state(project_root: str) -> Optional[dict]:
    """Read ``.rddf/state/roadmap-state.json``.

    Returns the parsed dict, or ``None`` if the file is missing, contains
    invalid JSON, or the top-level value is not a dict.
    """
    path = _state_path(project_root, "roadmap-state.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def read_proposal_suggestions(project_root: str) -> Optional[list[dict]]:
    """Read ``proposal-suggestions.md`` as a JSON array.

    The file is a JSON array of suggestion dicts (despite the ``.md``
    extension - see ``docs/proposal-suggestions-format``). Returns the
    list, or ``None`` if the file is missing, empty, or contains invalid
    JSON / non-array data.
    """
    path = os.path.join(project_root, "proposal-suggestions.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except (FileNotFoundError, OSError):
        return None
    if not content:
        return None
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    return data


def list_worktrees() -> list[dict]:
    """List git worktrees via ``git worktree list --porcelain``.

    Returns a list of dicts, one per worktree, each with keys:
      - ``path`` (str|None): absolute path to the worktree
      - ``branch`` (str|None): branch ref (e.g. ``refs/heads/main``),
        or ``None`` for detached HEAD
      - ``is_openspec`` (bool): ``True`` if branch starts with
        ``refs/heads/openspec/``

    Returns an empty list on any error (git not found, timeout, or
    non-git directory). Never raises.
    """
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []

    worktrees: list[dict] = []
    current: dict = {}
    for line in result.stdout.splitlines():
        if not line:
            # Blank line separates records.
            if current:
                worktrees.append(current)
                current = {}
            continue
        parts = line.split(None, 1)
        if not parts:
            continue
        key = parts[0]
        value = parts[1] if len(parts) > 1 else None
        if key == "worktree":
            current["path"] = value
        elif key == "branch":
            current["branch"] = value
    # Flush the last record (no trailing blank line guarantee).
    if current:
        worktrees.append(current)

    # Normalize: ensure all three keys present and compute is_openspec.
    for wt in worktrees:
        wt.setdefault("path", None)
        wt.setdefault("branch", None)
        branch = wt.get("branch")
        wt["is_openspec"] = bool(
            branch is not None and branch.startswith("refs/heads/openspec/")
        )

    return worktrees


def list_change_dirs(project_root: str) -> list[str]:
    """List non-archived change directories under ``openspec/changes/``.

    Returns a sorted list of directory names (not full paths), excluding
    ``archive``. Returns an empty list if the directory does not exist
    or is empty. Never raises.
    """
    changes_dir = os.path.join(project_root, "openspec", "changes")
    try:
        entries = os.listdir(changes_dir)
    except (FileNotFoundError, OSError):
        return []
    names = [
        e for e in entries
        if e != "archive"
        and os.path.isdir(os.path.join(changes_dir, e))
    ]
    return sorted(names)
