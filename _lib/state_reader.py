"""Shared read-only data layer for all CLI subcommands.

This module provides 8 fine-grained functions that each read from a
specific state source (``.rddf/state/*.json``, `<a href=".rddf/improvements/*.md + improvement-approved.md``,
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
  The single exception is ``_parse_improvement_meta``, which *optionally*
  uses PyYAML (already a declared dep, and the same parser
  ``_lib/planner_attach.py`` uses for the very same files); when PyYAML is
  unavailable it falls back to the legacy inline-meta parser.

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
    list_worktrees            -> list[dict]  (empty on error, never None)
    list_change_dirs          -> list[str]   (empty on error, never None)
    read_improvement_entries  -> list[dict]  (empty on error, never None)
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from typing import Optional

from skills._lib.iteration.store import _read_unlocked, _read_unlocked_verbose

logger = logging.getLogger(__name__)

# State directory relative to project root (gitignored, main repo only).
_STATE_DIR = os.path.join(".rddf", "state")

#: Top-level ``key: value`` line of a front-matter block (naive-scan
#: fallback for blocks that are not valid YAML). The key may not start with
#: whitespace, ``:``, ``-`` (list item) or ``#`` (comment).
_FM_KEY_RE = re.compile(r"^(?![-#])([^\s:][^:]*):[ \t]*(.*)$")


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


def read_design_handoff(project_root: str) -> Optional[dict]:
    """Read ``.rddf/state/.design-handoff.json``.

    Returns the parsed dict, or ``None`` if the file is missing, contains
    invalid JSON, or the top-level value is not a dict.
    """
    path = _state_path(project_root, ".design-handoff.json")
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


def read_planner_handoff(project_root: str) -> Optional[dict]:
    """Read ``.rddf/state/.planner-handoff.json`` (v4 planner handoff).

    Returns the parsed dict, or ``None`` if the file is missing, contains
    invalid JSON, or the top-level value is not a dict. A corrupt file is
    therefore indistinguishable from a missing one — callers MUST treat
    both as "planner stage not complete" rather than silently advancing.
    """
    path = _state_path(project_root, ".planner-handoff.json")
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

    Callers that need to distinguish missing from corrupt should use
    :func:`read_iteration_or_corrupt` instead.
    """
    path = _state_path(project_root, "iteration.json")
    return _read_unlocked(path)


def read_iteration_or_corrupt(project_root: str) -> tuple[Optional[dict], Optional[str]]:
    """Like :func:`read_iteration` but distinguishes missing from corrupt.

    Returns:
        ``(data, None)`` on success or when the file is missing.
        ``(None, error_message)`` if the file exists but is corrupt
        (invalid JSON or schema-invalid). The error message is safe
        to print and includes the JSON path to the bad entry.

    Callers that need to surface corrupt-file diagnostics to users
    (e.g. ``status_cmd.py``) should use this instead of
    :func:`read_iteration`. The original ``read_iteration`` is kept
    for backward compatibility — its existing callers (guide
    recommender, intake phases) are unchanged.

    Created: fix-rddf-status-corrupt-message (P1, 2026-08-05).
    """
    path = _state_path(project_root, "iteration.json")
    return _read_unlocked_verbose(path)


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


def _scan_meta_lines(block: str) -> dict[str, str]:
    """Naive ``key: value`` scan of a front-matter block.

    Used **only** as a fallback when the block is not valid YAML (e.g. a
    multi-line plain scalar that contains a ``:``). It recovers the top-level
    keys — indented continuation lines are appended to the previous key's
    value — so one malformed scalar does not cost the whole metadata set.
    """
    out: dict[str, str] = {}
    last_key: str | None = None
    for line in block.split("\n"):
        if not line.strip():
            continue
        if line[:1] in (" ", "\t"):
            # Indented ⇒ continuation of the previous key's value.
            if last_key is not None:
                merged = f"{out[last_key]} {line.strip()}".strip()
                out[last_key] = merged
            continue
        match = _FM_KEY_RE.match(line)
        if not match:
            last_key = None
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key] = value
        last_key = key
    return out


def _front_matter_error(content: str, exc: Exception) -> str:
    """Describe a broken YAML front matter with a field-level location.

    PyYAML's message names a line/column *inside the parsed block* but never
    shows the offending text — the reader is left guessing which field broke.
    We therefore append the file line number and its content.

    Line arithmetic: the block starts at file line 1 (``---``) and the parsed
    slice starts at file line 2 ⇒ a 0-based block line ``n`` is file line
    ``n + 2``.
    """
    message = " ".join(str(exc).split())
    mark = getattr(exc, "problem_mark", None)
    if mark is None:
        return "invalid YAML front matter: " + message
    lines = content.split("\n")
    file_line = int(getattr(mark, "line", 0)) + 2
    source = lines[file_line - 1].strip() if 0 < file_line <= len(lines) else ""
    if not source:
        return "invalid YAML front matter: " + message
    return (f"invalid YAML front matter: {message} "
            f"(front-matter line {file_line}: {source[:80]})")


def _parse_improvement_meta(
    content: str, errors: list[str] | None = None
) -> dict[str, object]:
    """Parse the metadata block of an improvement file.

    Three formats are supported (first match wins):

    1. **YAML front matter** — the current convention (per the ``add-improve``
       skill template): a ``---`` delimited block of ``key: value`` pairs.
    2. **Naive front-matter scan** — the block exists but is **not valid
       YAML** (a multi-line plain scalar containing ``:`` breaks the parse).
       The top-level keys are recovered line-by-line instead of the whole
       block being dropped; the failure is appended to ``errors`` when a
       list is supplied.
    3. **Legacy inline meta** — older files carry ``**key**: value`` pairs on
       the 3rd / 4th line of the file.

    Returns a dict of raw metadata (empty when nothing is found). Never raises.
    """
    if content.startswith("---\n"):
        end = content.find("\n---", 4)
        if end != -1:
            meta: dict[str, object] = {}
            try:
                import yaml
            except ImportError:  # pragma: no cover - PyYAML is a declared dep
                yaml = None  # type: ignore[assignment]
            if yaml is not None:
                parsed = None
                yaml_error: Exception | None = None
                try:
                    parsed = yaml.safe_load(content[4:end])
                except Exception as exc:  # noqa: BLE001 - malformed front matter
                    yaml_error = exc
                if isinstance(parsed, dict):
                    for key, value in parsed.items():
                        meta[str(key)] = value
                    return meta
                if yaml_error is not None:
                    if errors is not None:
                        # Collapse the multi-line PyYAML message into one line
                        # (the CLI prints errors as single bullets) and point at
                        # the offending line (field-level location).
                        errors.append(_front_matter_error(content, yaml_error))
                    fallback = _scan_meta_lines(content[4:end])
                    if fallback:
                        meta.update(fallback)
                        return meta

    meta = {}
    lines = content.split("\n")
    for idx in (2, 3):
        if len(lines) <= idx:
            continue
        for match in re.finditer(r"\*\*(\S+)\*\*:\s*([^|]+)", lines[idx]):
            meta[match.group(1)] = match.group(2).strip()
    return meta


def _first_str(meta: dict, *keys: str) -> str:
    """Return the first non-empty string value among ``keys`` (else "")."""
    for key in keys:
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def read_improvement_entries(project_root: str) -> list[dict]:
    """Read all improvement files from .rddf/improvements/ directory.

    Returns list of dicts with keys: name, priority, source, phase, category,
    type, status — plus every raw front-matter key verbatim.

    ``priority`` / ``phase`` / ``category`` / ``source`` / ``effort`` /
    ``status`` are normalized from either the English key (``priority``) or
    its Chinese alias (``优先级``), so callers do not need to know which
    convention a given project uses.
    """
    imp_dir = os.path.join(project_root, ".rddf/improvements")
    if not os.path.isdir(imp_dir):
        return []

    entries: list[dict] = []
    for fname in sorted(os.listdir(imp_dir)):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(imp_dir, fname)
        entry: dict = {"name": fname[:-3]}
        try:
            with open(fpath, encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        meta_errors: list[str] = []
        meta = _parse_improvement_meta(content, errors=meta_errors)
        for key, value in meta.items():
            if key == "name":
                # The file name is the canonical key (archive dirs are matched
                # against it) ⇒ front-matter "name" must not override it.
                continue
            entry[key] = value
        entry["priority"] = _first_str(meta, "priority", "优先级")
        entry["phase"] = _first_str(meta, "phase", "阶段")
        entry["category"] = _first_str(meta, "category", "分类")
        entry["source"] = _first_str(meta, "source", "来源")
        entry["effort"] = _first_str(meta, "effort", "工作量")
        entry["status"] = _first_str(meta, "status", "状态")
        if meta_errors:
            # Surfaced (not swallowed): a broken front matter silently costs
            # the whole metadata set (priority / phase / status), so callers
            # must be able to report it. See ``collect_pending().errors``.
            entry["meta_parse_error"] = "; ".join(meta_errors)
        entries.append(entry)
    return entries
