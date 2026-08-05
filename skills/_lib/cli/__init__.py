"""CLI subcommand routing table for ``python3 -m skills._lib.cli``.

This package is the single CLI entry point for rdd-workflow. Each
subcommand (``dashboard``, ``status``, ``sessions``) is implemented as a
separate ``*_cmd.py`` module exposing a ``cmd_<name>(args: list[str]) -> int``
function. The routing table here maps subcommand name -> handler callable.

Design (per ``docs/superpowers/specs/2026-07-20-dashboard-design.md``
§4.1): the routing table is a module-level constant so that
``list_commands()`` can be derived from it without duplicating names.
Handlers are imported lazily inside :func:`route` to keep import cost
low for ``--help``-style invocations and to avoid pulling in heavy
dependencies (e.g. ``dashboard`` package) when the user only wants
``status``.

Layering:

    cli/__init__.py        (this file - routing table + route/list_commands)
        ^
        |  delegates
        |
    cli/__main__.py        (entry point: arg parse + project root + route)
        ^
        |  calls route()
        |
    cli/<subcommand>_cmd.py (handler: cmd_<name>(args) -> int)

This module is import-safe: importing it does NOT import the handler
modules or any of their dependencies (``state_reader``, ``dashboard``,
``iteration``, ``rddf_session``). Only :func:`route` triggers lazy
imports.
"""
from __future__ import annotations

import os
import sys
import types
from typing import Callable, Dict

# ---------------------------------------------------------------------------
# Dash-bridge: register sys.modules aliases for dash-named skill packages.
#
# Python cannot ``import skills.rddf_session`` when the directory on disk
# is ``skills/rddf-session/`` (dashes are illegal in identifiers). The
# pytest conftest registers synthetic modules for this; standalone
# ``python3 -m skills._lib.cli`` invocations need the same aliases or
# ``sessions_cmd.py``'s import of ``RddfSessionCoordinator`` fails.
#
# Mirrors ``tests/conftest.py`` lines 29-43. Idempotent: skips already-
# registered module names so re-import is cheap.
# ---------------------------------------------------------------------------
_DASH_SKILLS = [
    ("guide-arch", "guide_arch"),
    ("guide-plan", "guide_plan"),
    ("guide-ship", "guide_ship"),
    ("rddf-session", "rddf_session"),
]
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
for _dash, _us in _DASH_SKILLS:
    for _level in ("", ".scripts"):
        _mod_name = f"skills.{_us}{_level}"
        if _mod_name not in sys.modules:
            _mod = types.ModuleType(_mod_name)
            _level_dir = _level.lstrip(".") if _level else _level
            _mod.__path__ = [
                os.path.join(_PROJECT_ROOT, "skills", _dash, _level_dir)
                if _level_dir
                else os.path.join(_PROJECT_ROOT, "skills", _dash)
            ]
            sys.modules[_mod_name] = _mod


# Subcommand -> fully-qualified handler import path.
# Each handler has signature ``cmd_<name>(args: list[str]) -> int`` and
# returns a process exit code (0 = success, non-zero = error).
_ROUTES: Dict[str, str] = {
    "archive": "skills._lib.cli.archive_cmd:cmd_archive",
    "archive-sync": "skills._lib.cli.archive_sync_cmd:cmd_archive_sync",
    "cleanup": "skills._lib.cli.cleanup_cmd:cmd_cleanup",
    "dashboard": "skills._lib.cli.dashboard_cmd:cmd_dashboard",
    "deps": "skills._lib.cli.deps_cmd:cmd_deps",
    "discover-ship-changes": "skills._lib.cli.discover_ship_changes_cmd:cmd_discover_ship_changes",
    "feature": "skills._lib.cli.feature_cmd:cmd_feature",
    "guide": "skills._lib.cli.guide_cmd:cmd_guide",
    "init": "skills._lib.cli.init_cmd:cmd_init",
    "monitor": "skills._lib.cli.monitor_cmd:cmd_monitor",
    "status": "skills._lib.cli.status_cmd:cmd_status",
    "sessions": "skills._lib.cli.sessions_cmd:cmd_sessions",
    "validate": "skills._lib.cli.validate_cmd:cmd_validate",
    "version": "skills._lib.cli.version_cmd:cmd_version",
}


def list_commands() -> list[str]:
    """Return the sorted list of registered subcommand names."""
    return sorted(_ROUTES.keys())


def route(subcommand: str, args: list[str]) -> int:
    """Route ``subcommand`` to its handler and invoke with ``args``.

    Imports the handler module lazily (only when this function is
    called) so that ``python3 -m skills._lib.cli help`` and similar
    light invocations do not pay the import cost of every subcommand.

    Args:
        subcommand: Subcommand name (e.g. ``"dashboard"``, ``"status"``,
            ``"sessions"``). Must be a key in :data:`_ROUTES`.
        args: Remaining CLI args to forward to the handler (e.g.
            ``["--json"]`` for ``dashboard --json``).

    Returns:
        The integer exit code from the handler.

    Raises:
        KeyError: If ``subcommand`` is not in :data:`_ROUTES`. Callers
            (typically :mod:`cli.__main__`) should catch this and print
            a friendly ``unknown command`` message.
    """
    if subcommand not in _ROUTES:
        raise KeyError(subcommand)

    # Lazy import: "skills._lib.cli.dashboard_cmd:cmd_dashboard"
    module_path, _, func_name = _ROUTES[subcommand].partition(":")
    import importlib

    module = importlib.import_module(module_path)
    handler: Callable[[list[str]], int] = getattr(module, func_name)
    return handler(args)


__all__ = ["route", "list_commands"]
