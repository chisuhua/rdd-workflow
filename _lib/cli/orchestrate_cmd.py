"""``rddf orchestrate`` — Python orchestrator for phase subprocess supervision.

Closes 4 blind spots in the bash trap ERR approach (see
``docs/superpowers/specs/2026-08-12-python-orchestrator-design.md`` §1.1):

- B1: Sub-scripts that don't source ``post_flow_wrap.sh`` never fire the trap.
- B2: Agents don't always comply with SKILL.md Phase Exit instruction.
- B3: Intermediate silent corruption (exit 0 but state already broken).
- B4: SIGKILL / OOM / laptop-close — zero signal, no trap, no finalize.

The headline feature is crash-survivable stale-trace detection (§5 of spec):
on first ``--subprocess`` invocation per phase entry, sweep trace dir for
unfinalized traces and report them as ``phase-interrupted``.

Trace format: JSONL at ``$RDDF_TRACE_DIR/<phase>-<session>-<pid>-<epoch>.jsonl``
(default ``.rddf/state/trace/``).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def cmd_orchestrate(argv: list[str]) -> int:
    """Entry point for ``rddf orchestrate <subcommand> [args]``."""
    parser = argparse.ArgumentParser(prog="rddf orchestrate")
    sub = parser.add_subparsers(dest="action", required=True)

    p_sub = sub.add_parser("subprocess", help="Run a subprocess and record its result")
    p_sub.add_argument("cmd", nargs=argparse.REMAINDER, help="Command + args to run")

    p_mark = sub.add_parser("mark-checkpoint", help="Insert a checkpoint event")
    p_mark.add_argument("--name", required=True)
    p_mark.add_argument("--state-marker", default="")

    p_fin = sub.add_parser("finalize", help="Close the trace and trigger analysis")

    p_sweep = sub.add_parser("sweep-stale-traces", help="Manually trigger sweep")

    args = parser.parse_args(argv)
    trace_dir = _get_trace_dir()

    if args.action == "subprocess":
        return _handle_subprocess(args.cmd, trace_dir)
    if args.action == "mark-checkpoint":
        return _handle_checkpoint(args.name, args.state_marker, trace_dir)
    if args.action == "finalize":
        return _handle_finalize(trace_dir)
    if args.action == "sweep-stale-traces":
        return _handle_sweep(trace_dir)
    return 2  # unreachable


def _get_trace_dir() -> Path:
    """Return the trace directory from env or default."""
    raw = os.environ.get("RDDF_TRACE_DIR", ".rddf/state/trace")
    return Path(raw).resolve()


def _handle_subprocess(cmd: list[str], trace_dir: Path) -> int:
    """Placeholder — filled in Task 3."""
    raise NotImplementedError("filled in Task 3")


def _handle_checkpoint(name: str, state_marker: str, trace_dir: Path) -> int:
    """Placeholder — filled in Task 4."""
    raise NotImplementedError("filled in Task 4")


def _handle_finalize(trace_dir: Path) -> int:
    """Placeholder — filled in Task 5."""
    raise NotImplementedError("filled in Task 5")


def _handle_sweep(trace_dir: Path) -> int:
    """Placeholder — filled in Task 10."""
    raise NotImplementedError("filled in Task 10")