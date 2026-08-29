"""``rddf sessions`` subcommand handler (read + write).

Six sub-modes (per ``docs/superpowers/specs/2026-07-20-dashboard-design.md``
§2, extended in v2 with write operations):

  - ``sessions`` (default, or ``sessions list``): list all sessions in
    a table.
  - ``sessions show <id>``: show single session detail.
  - ``sessions current``: show the current binding via
    :meth:`RddfSessionCoordinator.find_current_binding`.
  - ``sessions resume <id> --owner <opencode_session_id> [--force]``:
    resume a session under a new owner. Safety gate: ``--owner`` is
    required; conflict detection rejects unless ``--force`` is passed.
  - ``sessions abandon <id> --yes``: abandon a session. Safety gate:
    ``--yes`` is required to confirm the irreversible operation.
  - ``sessions gc``: garbage-collect active sessions whose heartbeats
    exceeded the 30-minute timeout, marking them as orphaned.

Usage::

    python3 -m skills._lib.cli sessions              # list all
    python3 -m skills._lib.cli sessions list         # same as above
    python3 -m skills._lib.cli sessions show rds_xxx # detail
    python3 -m skills._lib.cli sessions current      # current binding
    python3 -m skills._lib.cli sessions resume rds_xxx --owner host_123
    python3 -m skills._lib.cli sessions resume rds_xxx --owner host_123 --force
    python3 -m skills._lib.cli sessions abandon rds_xxx --yes
    python3 -m skills._lib.cli sessions gc

Read modes (list/show/current) never call mutating methods on
``RddfSessionCoordinator``. Write modes (resume/abandon/gc) each
enforce a safety gate before mutation:

  - ``resume``: ``--owner`` required + conflict detection (``--force`` override)
  - ``abandon``: ``--yes`` required (irreversible)
  - ``gc``: deterministic (no gate; only transitions stale active -> orphaned)

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
from typing import Optional, Tuple


def cmd_sessions(args: list[str]) -> int:
    """Handle ``rddf sessions [list|show <id>|current|resume|abandon|gc]``.

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
    if sub == "resume":
        return _resume_session(rest)
    if sub == "abandon":
        return _abandon_session(rest)
    if sub == "gc":
        return _gc_sessions(rest)
    if sub == "list-parallel":
        return _list_parallel_sessions()

    print(f"❌ sessions: unknown sub-command {sub!r}", file=sys.stderr)
    print(
        "   usage: rddf sessions [list|show <id>|current|resume <id>|abandon <id>|gc]",
        file=sys.stderr,
    )
    return 2


def _resolve_sessions_file() -> str:
    """Return the path to ``.rddf/state/sessions.json`` under project root."""
    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()
    return os.path.join(project_root, ".rddf", "state", "sessions.json")


def _resolve_owner_id() -> str:
    """Return the current OpenCode session id for binding lookup.

    Fallback uses the parent PID (opencode server process), which is
    stable across bash/python tool calls within one window.
    """
    owner = os.environ.get("OPENCODE_SESSION_ID")
    if owner:
        return owner
    return f"{socket.gethostname().split('.')[0]}_{os.getppid()}"


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


def _list_parallel_sessions() -> int:
    """``sessions list-parallel`` — group sessions by workflow_group.

    Prints a table where same-group sessions are shown together with a
    per-group "parallel" hint. Exits 0 on success, 1 on coordinator error.
    """
    try:
        coord = _get_coordinator()
    except ImportError as e:
        print(f"❌ sessions: failed to import RddfSessionCoordinator: {e}", file=sys.stderr)
        return 1

    try:
        sessions = coord.list_sessions()
    except Exception as e:
        print(f"❌ sessions list-parallel: {e}", file=sys.stderr)
        return 1

    if not sessions:
        print("📭 no sessions recorded")
        print('   create one via: skill_use("guide-arch"|"guide-design"|"guide-plan"|"guide-ship")')
        return 0

    from collections import defaultdict

    groups: dict = defaultdict(list)
    for s in sessions:
        groups[s.workflow_group or "independent"].append(s)

    print("📊 Parallel session groups")
    for group_name, members in sorted(groups.items()):
        print(f"\n▸ workflow_group: {group_name}  ({len(members)} sessions)")
        print(f"{'SESSION_ID':<32} {'KIND':<14} {'STATE':<10} {'CHANGES':<8}")
        print(f"{'-'*32} {'-'*14} {'-'*10} {'-'*8}")
        for s in members:
            sid = (s.session_id or "?")[:32]
            kind = (s.kind or "?")[:14]
            state = (s.state or "?")[:10]
            n_changes = len(s.attached_changes or [])
            print(f"{sid:<32} {kind:<14} {state:<10} {n_changes:<8}")
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
    print("usage: rddf sessions [list|show <id>|current|resume <id>|abandon <id>|gc]")
    print()
    print("Session management (read + write).")
    print()
    print("sub-commands:")
    print("  list                      List all sessions in a table (default)")
    print("  show <id>                 Show detail for a single session")
    print("  current                   Show the current session binding (via OPENCODE_SESSION_ID)")
    print("  resume <id> --owner <id>  Resume a session under a new owner (write)")
    print("  abandon <id> --yes        Abandon a session (irreversible, write)")
    print("  gc                        Garbage-collect timed-out sessions (write)")


# ---------------------------------------------------------------------------
# Write operations: resume / abandon / gc
#
# These three subcommands mutate sessions.json. Each enforces a safety gate
# before invoking any mutating method on RddfSessionCoordinator:
#
#   resume:  --owner is required, and a conflict check rejects unless --force
#            is also passed (mirrors ADR-0017 §3 4-option soft prompt).
#   abandon: --yes is required (the operation is irreversible).
#   gc:      deterministic - only transitions active sessions whose
#            last_heartbeat exceeds the 30-minute timeout to orphaned. No
#            user gate required.
#
# The coordinator itself loads/saves sessions.json via its own atomic-write
# helper; we DO NOT read or write sessions.json directly here (the spec
# mentions json.load for the read path, but the coordinator's find_session
# + detect_conflict + transfer_ownership + update_session_status + abandon
# + check_heartbeat_timeouts API already encapsulates the file I/O safely
# under file lock, and that is the canonical write path used by the rest
# of the codebase). Using the coordinator avoids the race condition where
# a read-then-write window could clobber concurrent updates.
# ---------------------------------------------------------------------------


def _parse_resume_args(
    rest: list[str],
) -> Tuple[Optional[str], Optional[str], bool]:
    """Parse ``resume <id> --owner <owner> [--force]``.

    Returns ``(session_id, owner, force)``. ``session_id`` is None if no
    positional id was supplied. ``owner`` is None if ``--owner`` was not
    supplied (caller must reject). ``force`` is True iff ``--force`` is
    present.
    """
    session_id: Optional[str] = None
    owner: Optional[str] = None
    force = False
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok == "--owner":
            if i + 1 >= len(rest):
                # Missing value for --owner - leave owner as None so the
                # caller emits the "required" error.
                break
            owner = rest[i + 1]
            i += 2
            continue
        if tok.startswith("--owner="):
            owner = tok[len("--owner=") :]
            i += 1
            continue
        if tok == "--force":
            force = True
            i += 1
            continue
        # First non-flag token is the session id. Subsequent non-flag
        # tokens are ignored (we only expect one positional).
        if session_id is None and not tok.startswith("-"):
            session_id = tok
        i += 1
    return session_id, owner, force


def _resume_session(rest: list[str]) -> int:
    """``sessions resume <id> --owner <opencode_session_id> [--force]``.

    Safety gates:
      1. ``--owner`` is required (reject with exit 1 if missing).
      2. ``<id>`` is required (reject with exit 2 if missing).
      3. If another opencode session owns an active session of the same
         kind, reject unless ``--force`` is also passed.

    On success: transfers ownership to the new owner, refreshes the
    heartbeat, and transitions state to ``active`` (idempotent if
    already active).
    """
    session_id, owner, force = _parse_resume_args(rest)

    if session_id is None:
        print("❌ sessions resume: missing <id> argument", file=sys.stderr)
        print(
            "   usage: rddf sessions resume <id> --owner <opencode_session_id> [--force]",
            file=sys.stderr,
        )
        return 2
    if not owner:
        print("❌ Error: --owner required", file=sys.stderr)
        print(
            "   usage: rddf sessions resume <id> --owner <opencode_session_id> [--force]",
            file=sys.stderr,
        )
        return 1

    try:
        coord = _get_coordinator()
    except ImportError as e:
        print(f"❌ sessions: failed to import RddfSessionCoordinator: {e}", file=sys.stderr)
        return 1

    # Look up the session first so we can (a) report not-found cleanly and
    # (b) run conflict detection against its kind.
    try:
        target = coord.find_session(session_id)
    except Exception as e:
        print(f"❌ sessions resume: {e}", file=sys.stderr)
        return 1

    if target is None:
        print(f"❌ session '{session_id}' not found", file=sys.stderr)
        return 1

    # Conflict detection: another opencode session owning an active session
    # of the same kind means resuming would silently hijack it. The 4-option
    # soft prompt (ADR-0017 §3) is the user-side resolution; here we expose
    # --force as the CLI equivalent of "I know what I'm doing".
    try:
        conflict = coord.detect_conflict(target.kind, owner)
    except Exception as e:
        print(f"❌ sessions resume: conflict check failed: {e}", file=sys.stderr)
        return 1

    if conflict is not None and not force:
        print(
            "❌ Conflict: another session owns an active session of this kind. "
            "Use --force to override.",
            file=sys.stderr,
        )
        return 1

    # Safe to resume: transfer ownership + ensure state is active.
    try:
        coord.transfer_ownership(session_id, owner)
        # transfer_ownership refreshes the heartbeat but does not change
        # state; an orphaned session needs to be explicitly re-activated.
        # update_session_status is idempotent on already-active sessions
        # (it just refreshes the heartbeat again).
        coord.update_session_status(session_id, "active")
    except Exception as e:
        print(f"❌ sessions resume: {e}", file=sys.stderr)
        return 1

    print(f"✅ session {session_id} resumed by {owner}")
    return 0


def _abandon_session(rest: list[str]) -> int:
    """``sessions abandon <id> --yes``.

    Safety gate: ``--yes`` is required (irreversible operation).
    """
    session_id: Optional[str] = None
    confirmed = False
    for tok in rest:
        if tok == "--yes":
            confirmed = True
            continue
        if tok in ("-y", "--yes=true", "--yes=true"):
            confirmed = True
            continue
        if tok.startswith("--yes="):
            # Accept --yes=false / --yes=true (anything except explicit
            # false counts as confirmation, mirroring confirm-style flags).
            confirmed = tok.split("=", 1)[1].lower() not in ("false", "0", "")
            continue
        if session_id is None and not tok.startswith("-"):
            session_id = tok

    if session_id is None:
        print("❌ sessions abandon: missing <id> argument", file=sys.stderr)
        print("   usage: rddf sessions abandon <id> --yes", file=sys.stderr)
        return 2
    if not confirmed:
        print(
            f"⚠️ Abandon session '{session_id}'? This cannot be undone. "
            "Use --yes to confirm."
        )
        return 1

    try:
        coord = _get_coordinator()
    except ImportError as e:
        print(f"❌ sessions: failed to import RddfSessionCoordinator: {e}", file=sys.stderr)
        return 1

    try:
        coord.abandon(session_id)
    except Exception as e:
        print(f"❌ sessions abandon: {e}", file=sys.stderr)
        return 1

    print(f"✅ session {session_id} abandoned")
    return 0


def _gc_sessions(rest: list[str]) -> int:
    """``sessions gc``.

    Heartbeat garbage collection. No user gate required - this is a
    deterministic operation that only transitions stale active sessions
    (last_heartbeat older than 30 minutes) to orphaned state.

    Any extra args are ignored (``gc`` takes no flags).
    """
    try:
        coord = _get_coordinator()
    except ImportError as e:
        print(f"❌ sessions: failed to import RddfSessionCoordinator: {e}", file=sys.stderr)
        return 1

    try:
        newly_orphaned = coord.check_heartbeat_timeouts()
    except Exception as e:
        print(f"❌ sessions gc: {e}", file=sys.stderr)
        return 1

    if newly_orphaned:
        n = len(newly_orphaned)
        print(f"✅ Marked {n} sessions as orphaned")
        for sid in newly_orphaned:
            print(f"   - {sid}")
    else:
        print("✅ no timed-out sessions")
    return 0


__all__ = ["cmd_sessions"]
