"""``rddf monitor`` subcommand handler.

Real-time dashboard aggregating 4 read-only panels:

  - **Sessions** (ADR-0017): list active/orphaned rddf-sessions with
    kind, state, owner. Heartbeat GC is NOT auto-run (the user must
    invoke ``rddf sessions gc`` explicitly).
  - **Worktrees**: openspec worktrees with branch + count summary.
  - **Event log**: last 5 events from ``.rddf/state/event-log.jsonl``.
  - **Phase status**: arch-handoff + plan-handoff presence + counts.

Usage::

    python3 -m skills._lib.cli monitor              # single render
    python3 -m skills._lib.cli monitor --watch=5    # refresh every 5s
    python3 -m skills._lib.cli monitor --watch 5    # equivalent

The project root is injected by ``cli.__main__`` via the
``RDDF_PROJECT_ROOT`` env var; falls back to ``os.getcwd()``.

This module is independent of the ``dashboard`` package: it reads
state files directly via :mod:`skills._lib.state_reader` plus a
handful of inline file reads. This keeps the monitor path cheap
(fewer imports) and resilient (a broken dashboard package does not
break ``rddf monitor``).
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone


def cmd_monitor(args: list[str]) -> int:
    """Handle ``rddf monitor [--watch=N]``.

    Args:
        args: Args after the ``monitor`` token. Recognized flags:
            ``--watch=N`` or ``--watch N`` (positive integer; default 0
            = single render, no refresh), ``-h``/``--help``.

    Returns:
        0 on success, 1 on error, 2 on bad flag.
    """
    watch_interval = 0
    i = 0
    while i < len(args):
        tok = args[i]
        if tok in ("-h", "--help"):
            _print_help()
            return 0
        if tok.startswith("--watch="):
            watch_interval = tok[len("--watch="):]
            i += 1
            continue
        if tok == "--watch":
            if i + 1 >= len(args):
                print("❌ monitor: --watch requires a value", file=sys.stderr)
                return 2
            watch_interval = args[i + 1]
            i += 2
            continue
        print(f"❌ monitor: unknown flag {tok!r}", file=sys.stderr)
        print("   usage: rddf monitor [--watch=N]", file=sys.stderr)
        return 2

    # Validate interval: must be a positive integer (0 = single render).
    if not watch_interval or watch_interval == "0":
        watch_n = 0
    else:
        try:
            watch_n = int(watch_interval)
            if watch_n <= 0:
                raise ValueError
        except ValueError:
            print(
                f"❌ monitor: invalid --watch value {watch_interval!r} "
                f"(expected positive integer, e.g. --watch=5)",
                file=sys.stderr,
            )
            return 2

    project_root = os.environ.get("RDDF_PROJECT_ROOT") or os.getcwd()

    if watch_n > 0:
        try:
            while True:
                print("\x1b[2J\x1b[H", end="")
                _render_monitor(project_root)
                time.sleep(watch_n)
        except KeyboardInterrupt:
            print()
            print("退出监控.")
            return 0
    else:
        _render_monitor(project_root)
        return 0


def _render_monitor(project_root: str) -> None:
    """Print the 4-panel monitor dashboard to stdout."""
    from skills._lib.state_reader import (
        list_worktrees,
        read_arch_handoff,
        read_plan_handoff,
        read_sessions,
    )

    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%d %H:%M:%S UTC")
    print()
    print(f"📡 spec-workflow 实时监控  (更新于 {ts})")
    print()

    # Panel 1: Sessions
    print("── rddf-sessions (ADR-0017) ──")
    sessions = read_sessions(project_root)
    if sessions is None:
        print("(no sessions)")
    elif not sessions:
        print("(no sessions)")
    else:
        print(f"{'ID':<30} {'KIND':<14} {'STATE':<10} {'OWNER':<24}")
        for s in sessions:
            sid = (s.get("session_id") or "?")[:30]
            kind = (s.get("kind") or "?")[:14]
            state = (s.get("state") or "?")[:10]
            owner = (s.get("owner_opencode_session_id") or "-")[:24]
            print(f"{sid:<30} {kind:<14} {state:<10} {owner:<24}")
    print()

    # Panel 2: Worktrees
    print("── Active Worktrees ──")
    worktrees = list_worktrees()
    openspec_wts = [w for w in worktrees if w.get("is_openspec")]
    if not openspec_wts:
        print("(no worktrees)")
    else:
        for w in openspec_wts:
            wt_path = w.get("path") or "?"
            branch = w.get("branch") or "?"
            # Shorten branch ref: refs/heads/openspec/foo -> openspec/foo
            if branch.startswith("refs/heads/"):
                branch = branch[len("refs/heads/"):]
            wt_name = os.path.basename(wt_path.rstrip("/")) or wt_path
            print(f".rddf/wt/{wt_name} -> {branch}")
        print(f"{len(openspec_wts)} active openspec worktrees")
    print()

    # Panel 3: Event log (last 5)
    print("── Recent Events ──")
    event_path = os.path.join(project_root, ".rddf", "state", "event-log.jsonl")
    if not os.path.isfile(event_path):
        print("(event-log.jsonl 不存在)")
    else:
        try:
            with open(event_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            recent = lines[-5:] if len(lines) >= 5 else lines
            if not recent:
                print("(empty event log)")
            else:
                import json as _json
                for line in recent:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = _json.loads(line)
                    except Exception:
                        continue
                    ts_short = (evt.get("timestamp") or "?")[:16]
                    msg = (evt.get("message") or "")[:60]
                    print(f"{ts_short}  {msg}")
        except OSError as e:
            print(f"(event-log read failed: {e})")
    print()

    # Panel 4: Phase status (arch + plan handoffs)
    print("── Phase Status ──")
    arch = read_arch_handoff(project_root)
    if arch is None:
        print("⏳ arch not done (no .arch-handoff.json)")
    else:
        adr_count = arch.get("adr_count")
        if adr_count is None:
            adr_count = len(arch.get("completed_adr_ids") or [])
        print(f"✅ arch done ({adr_count} ADRs)")

    plan = read_plan_handoff(project_root)
    if plan is None:
        print("⏳ plan not done (no .plan-handoff.json)")
    else:
        n_active = plan.get("active_changes")
        if n_active is None:
            n_active = len(plan.get("committed_changes") or [])
        print(f"✅ plan done ({n_active} active change"
              f"{'s' if n_active != 1 else ''})")
    print()


def _print_help() -> None:
    print("usage: rddf monitor [--watch=N]")
    print()
    print("Real-time monitor dashboard (sessions + worktrees + events + phase).")
    print()
    print("flags:")
    print("  --watch=N    Refresh every N seconds (e.g. --watch=5). Ctrl+C to exit.")
    print("  --watch N    Equivalent form.")
    print("  (default)    Single render, then exit.")


__all__ = ["cmd_monitor"]
