"""``rddf iteration`` subcommand handler (lint + allowed-fields).

Created: rddf-iteration-strict-schema (P1, 2026-08-05).
Purpose: write-side pre-check tools that complement the read-side
corrupt-message fix (fix-rddf-status-corrupt-message). Before AI
agents write to iteration.json, they can call ``rddf iteration
allowed-fields`` to learn the per-change field whitelist, and after
writing they can call ``rddf iteration lint .`` to validate without
triggering the backup-and-rebuild path.

Usage::

    rddf iteration lint [path]
    rddf iteration allowed-fields [path]

Both commands are read-only: no file writes, no backup creation.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Tuple


def _resolve_project_root(arg: str | None) -> str:
    """Resolve project root from CLI arg or env var, falling back to cwd.

    Priority: explicit arg > ``RDDF_PROJECT_ROOT`` env > ``os.getcwd()``.
    """
    if arg and arg != ".":
        return os.path.abspath(arg)
    return os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()


def _get_per_change_property_names() -> List[str]:
    """Extract per-change item property names from iteration_schema.json.

    Returns the list of field names allowed in a single change entry,
    e.g. ``["name", "status", "added_at", ...]``.
    """
    from skills._lib.iteration.schema import _load_schema
    schema = _load_schema()
    changes_props = (
        schema.get("properties", {})
        .get("changes", {})
        .get("items", {})
        .get("properties", {})
    )
    return list(changes_props.keys())


def _collect_invalid_fields(
    data: dict | None, valid_fields: List[str]
) -> List[Tuple[str, str]]:
    """Return list of ``(path, field_name)`` for fields not in valid_fields.

    Walks the entire data tree and reports any per-change entry
    fields that are not in the per-change property whitelist. Top-level
    fields are validated against the root schema's properties.
    """
    if data is None:
        return []
    invalid = []
    root_valid = set(valid_fields) | {"version", "updated_at",
                                     "current_phase", "changes", "feature_view"}
    for field in data:
        if field not in root_valid:
            invalid.append(("$", field))

    for i, change in enumerate(data.get("changes", []) or []):
        if not isinstance(change, dict):
            continue
        for field in change:
            if field not in valid_fields:
                invalid.append((f"changes.{i}", field))
    return invalid


def cmd_iteration_lint(args: list[str]) -> int:
    """Validate iteration.json without writing any files or backups.

    Args:
        args: First positional arg is the project root (``.`` for cwd).

    Returns:
        0 if iteration.json is valid or missing (no work to do);
        1 if iteration.json has schema issues (invalid JSON or invalid
          fields) — the file has diagnostics the user must fix;
        2 if the file is unreadable for reasons unrelated to schema
          (e.g. permission denied). Rare in practice.
    """
    project_root = _resolve_project_root(args[0] if args else ".")
    iter_path = os.path.join(project_root, ".rddf", "state", "iteration.json")

    if not os.path.isfile(iter_path):
        print(f"ℹ️  iteration.json not found at {iter_path}")
        return 0

    from skills._lib.state_reader import read_iteration_or_corrupt
    iter_data, read_error = read_iteration_or_corrupt(project_root)
    allowed_fields = _get_per_change_property_names()
    if read_error is not None:
        if read_error.startswith("invalid JSON"):
            print(f"❌ iteration.json is not valid JSON: {read_error}")
            print(f"   allowed per-change fields: {', '.join(allowed_fields)}")
            return 2
        print(f"❌ iteration.json fails schema validation")
        print(f"   path: {iter_path}")
        print(f"   error: {read_error}")
        print(f"   allowed per-change fields: {', '.join(allowed_fields)}")
        print("   fix: restore from .rddf/state/iteration.json.corrupt.<ts> "
              "backup, or edit the file manually")
        return 1

    invalid = _collect_invalid_fields(iter_data, allowed_fields)
    if invalid:
        print(f"❌ iteration.json has {len(invalid)} invalid field(s):")
        for path, field in invalid:
            print(f"   - {path}: '{field}' is not in the per-change schema")
        print()
        print(f"   allowed per-change fields: {', '.join(allowed_fields)}")
        return 1

    print("✅ iteration.json: no issues found")
    return 0


def cmd_iteration_allowed_fields(args: list[str]) -> int:
    """Print the per-change field whitelist (for AI pre-write checks).

    Args:
        args: First positional arg is the project root (``.`` for cwd).

    Returns:
        0 always (no errors, this is purely informational).
    """
    project_root = _resolve_project_root(args[0] if args else ".")

    state_dir = os.path.join(project_root, ".rddf", "state")
    if not os.path.isdir(state_dir):
        print(f"ℹ️  not a rdd-workflow project (no {state_dir})")
        return 0

    valid_fields = _get_per_change_property_names()
    print("per-change iteration.json fields (use these, nothing else):")
    for f in valid_fields:
        print(f"  {f}")
    return 0


def cmd_iteration(args: list[str]) -> int:
    """Dispatch ``rddf iteration <subcommand> [args...]``.

    Subcommands:
      - lint: validate iteration.json without writing
      - allowed-fields: print per-change field whitelist
    """
    if not args or args[0] in ("-h", "--help", "help"):
        print("usage: rddf iteration <subcommand> [args...]")
        print()
        print("subcommands:")
        print("  lint [path]           Validate iteration.json (read-only)")
        print("  allowed-fields [path] Print per-change field whitelist")
        return 0

    sub = args[0]
    rest = args[1:]
    if sub == "lint":
        return cmd_iteration_lint(rest)
    if sub == "allowed-fields":
        return cmd_iteration_allowed_fields(rest)
    print(f"❌ unknown iteration subcommand: {sub}", file=sys.stderr)
    print("   available: lint, allowed-fields", file=sys.stderr)
    return 2


__all__ = ["cmd_iteration", "cmd_iteration_lint", "cmd_iteration_allowed_fields"]
