"""``rddf sessions`` subcommand handler (read-only).

Three sub-modes (per ``docs/superpowers/specs/2026-07-20-dashboard-design.md``
§2):

  - ``sessions`` (default, or ``sessions list``): list all sessions in
    a table.
  - ``sessions show <id>``: show single session detail.
  - ``sessions current``: show the current binding via
    :meth:`RddfSessionCoordinator.find_current_binding`.

Usage::

    python3 -m skills._lib.cli sessions              # list all
    python3 -m skills._lib.cli sessions list         # same as above
    python3 -m skills._lib.cli sessions show rds_xxx # detail
    python3 -m skills._lib.cli sessions current      # current binding

All three modes are strictly read-only - they never call
``create_session``, ``update_session_status``, ``attach_change``, or
any other mutating method on ``RddfSessionCoordinator``. Write
operations (resume/abandon/gc) are deferred to v2 per the spec §6.

The project root is injected by ``cli.__main__`` via the
``RDDF_PROJECT_ROOT`` env var; falls back to ``os.getcwd()``.

The OpenCode session id (used by ``current``) is read from the
``OPENCODE_SESSION_ID`` env var with a ``<hostname>_<pid>`` fallback,
mirroring the bash pattern in ``rddf-session/SKILL.md`` line 87.
"""
from __future__ import annotations

import os
import socket
import sys


def cmd_sessions(args: list[str]) -> int:
    """Handle ``rddf sessions [list|show <id>|current]``.

    Args:
        args: Args after the ``sessions`` token. The first positional
            arg (if any) selects the sub-mode; remaining args are
            sub-mode-specific (e.g. the session id for ``show``).

    Returns:
        0 on success, 1 on error, 2 on bad usage.
    """
    # Parse sub-mode.
    if not args:
        # Default: list all sessions (per spec §2 "sessions (default) -> List all")
        return _list_sessions()
    if args[0] in ("-h", "--help", "help"):
        _print_help()
        return 0

    sub = args[0]
    rest = args[1:]

    if sub == "list":
        return _list_sessions()
    if sub == "show":
        if not rest:
            print("❌ sessions show: missing <id> argument", file=sys.stderr)
            print("   usage: rddf sessions show <id>", file=sys.stderr)
            return 2
        return _show_session(rest[0])
    if sub == "current":
        return _current_session()

    print(f"❌ sessions: unknown sub-command {sub!r}", file=sys.stderr)
    print("   usage: rddf sessions [list|show <id>|current]", file=sys.stderr)
    return 2


def _resolve_sessions_file() -> str:
    """Return the path to ``.rddf/state/sessions.json`` under project root."""
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    return os.path.join(project_root, ".rddf", "state", "sessions.json")


def _resolve_owner_id() -> str:
    """Return the current OpenCode session id for binding lookup.

    Mirrors the bash pattern in ``rddf-session/SKILL.md`` line 87:
    ``OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"``.
    """
    owner = os.environ.get("OPENCODE_SESSION_ID")
    if owner:
        return owner
    return f"{socket.gethostname().split('.')[0]}_{os.getpid()}"


def _get_coordinator():
    """Lazy-import and construct RddfSessionCoordinator.

    Import is deferred so that ``rddf help`` and other subcommands do
    not pay the cost of importing the rddf_session module (which pulls
    in fcntl, jsonschema, atomic_write, etc.).
    """
    from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator

    return RddfSessionCoordinator(sessions_file=_resolve_sessions_file())


def _list_sessions() -> int:
    """List all sessions in a table."""
    try:
        coord = _get_coordinator()
    except ImportError as e:
        print(f"❌ sessions: failed to import RddfSessionCoordinator: {e}", file=sys.stderr)
        return 1

    try:
        sessions = coord.list_sessions()
    except Exception as e:
        print(f"❌ sessions list: {e}", file=sys.stderr)
        return 1

    if not sessions:
        print("📭 no sessions recorded")
        print('   create one via: skill_use("guide-arch"|"guide-plan"|"guide-ship")')
        return 0

    owner_id = _resolve_owner_id()
    print("📊 All rddf-sessions")
    print(f"   current owner lookup: {owner_id}")
    print()
    print(f"{'SESSION_ID':<32} {'KIND':<14} {'STATE':<10} {'OWNER':<24} {'CHANGES':<8}")
    print(f"{'-' * 32} {'-' * 14} {'-' * 10} {'-' * 24} {'-' * 8}")

    for s in sessions:
        sid = (s.session_id or "?")[:32]
        kind = (s.kind or "?")[:14]
        state = (s.state or "?")[:10]
        owner = (s.owner_opencode_session_id or "-")[:24]
        n_changes = len(s.attached_changes or [])
        print(f"{sid:<32} {kind:<14} {state:<10} {owner:<24} {n_changes:<8}")

    return 0


def _show_session(session_id: str) -> int:
    """Show detail for a single session."""
    try:
        coord = _get_coordinator()
    except ImportError as e:
        print(f"❌ sessions: failed to import RddfSessionCoordinator: {e}", file=sys.stderr)
        return 1

    try:
        s = coord.find_session(session_id)
    except Exception as e:
        print(f"❌ sessions show: {e}", file=sys.stderr)
        return 1

    if s is None:
        print(f"❌ session not found: {session_id}")
        return 1

    print(f"session_id:                {s.session_id}")
    print(f"kind:                      {s.kind}")
    print(f"state:                     {s.state}")
    print(f"owner_opencode_session_id: {s.owner_opencode_session_id or '-'}")
    print(f"parent_session_id:         {s.parent_session_id or '-'}")
    goal = s.goal
    if isinstance(goal, dict):
        intent = goal.get("intent")
        subject = goal.get("subject")
        if intent and subject:
            print(f"goal:                      {intent}: {subject}")
        elif subject:
            print(f"goal:                      {subject}")
        elif intent:
            print(f"goal:                      {intent}")
        else:
            print("goal:                      -")
    elif goal:
        print(f"goal:                      {goal}")
    else:
        print("goal:                      -")
    print(f"context_pointer:           {s.context_pointer or '-'}")
    print(f"started_at:                {s.started_at or '-'}")
    print(f"last_heartbeat:            {s.last_heartbeat or '-'}")
    print(f"ended_at:                  {s.ended_at or '-'}")
    print(f"end_reason:                {s.end_reason or '-'}")
    if s.attached_changes:
        print(f"attached_changes ({len(s.attached_changes)}):")
        for c in s.attached_changes:
            print(f"  - {c}")
    else:
        print("attached_changes:          (none)")
    return 0


def _current_session() -> int:
    """Show the current session binding for this OpenCode session."""
    try:
        coord = _get_coordinator()
    except ImportError as e:
        print(f"❌ sessions: failed to import RddfSessionCoordinator: {e}", file=sys.stderr)
        return 1

    owner_id = _resolve_owner_id()
    try:
        s = coord.find_current_binding(owner_id)
    except Exception as e:
        print(f"❌ sessions current: {e}", file=sys.stderr)
        return 1

    if s is None:
        print(f"📭 no active session bound to owner {owner_id}")
        print('   start one via: skill_use("guide-arch"|"guide-plan"|"guide-ship")')
        return 0

    print(f"📍 current binding for owner {owner_id}:")
    print(f"   session_id: {s.session_id}")
    print(f"   kind:       {s.kind}")
    print(f"   state:      {s.state}")
    if s.attached_changes:
        print(f"   changes ({len(s.attached_changes)}):")
        for c in s.attached_changes:
            print(f"     - {c}")
    else:
        print("   changes:    (none)")
    if s.last_heartbeat:
        print(f"   heartbeat:  {s.last_heartbeat}")
    return 0


def _print_help() -> None:
    print("usage: rddf sessions [list|show <id>|current]")
    print()
    print("Read-only session management.")
    print()
    print("sub-commands:")
    print("  list           List all sessions in a table (default)")
    print("  show <id>      Show detail for a single session")
    print("  current        Show the current session binding (via OPENCODE_SESSION_ID)")


__all__ = ["cmd_sessions"]
