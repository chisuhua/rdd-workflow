"""CLI dispatcher for `rddf planner ...` subcommands (Stage 2 MVP).

Subcommands:
  status                    read-only sprint snapshot
  sync [--apply] [--dry-run]  default --dry-run; --apply writes state
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from _lib.planner_state import PlannerStateError, read_state
from _lib.planner_sync import apply_state, render_state


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project-root", default=".", help="Project root (default: cwd)")

    parser = argparse.ArgumentParser(
        prog="rddf planner",
        description="Manage rdd-planner sprint state (horizontal orchestrator, per ADR-0038).",
        parents=[common],
    )

    sub = parser.add_subparsers(dest="subcommand", required=True)

    sub.add_parser("status", help="Print sprint snapshot", parents=[common])

    p_sync = sub.add_parser("sync", help="Sync state (default: dry-run)", parents=[common])
    p_sync.add_argument("--apply", action="store_true", help="Actually write state and roadmap")
    p_sync.add_argument("--dry-run", action="store_true", help="Force dry-run (default)")

    return parser


def cmd_planner(args: List[str]) -> int:
    parser = _build_parser()
    ns = parser.parse_args(args)
    project_root = Path(ns.project_root).resolve()

    try:
        if ns.subcommand == "status":
            try:
                state = read_state(project_root)
                source = "stored"
            except PlannerStateError:
                state = render_state(project_root)
                source = "computed"
            sys.stdout.write(f"Sprint: {state['current_sprint']}\n")
            sys.stdout.write(f"Source: {source}\n")
            sys.stdout.write(f"Active projects: {len(state['active_projects'])}\n")
            sys.stdout.write(f"Unmapped proposals: {len(state['unmapped_proposals'])}\n")
            sys.stdout.write(f"Status: {state.get('last_sync_status', 'unknown')}\n")
            return 0

        if ns.subcommand == "sync":
            apply = ns.apply
            state = render_state(project_root)
            if not apply:
                sys.stdout.write(f"DRY-RUN: would write state and update roadmap.\n")
                sys.stdout.write(f"  Sprint: {state['current_sprint']}\n")
                sys.stdout.write(f"  Active: {len(state['active_projects'])}\n")
                sys.stdout.write(f"  Unmapped: {len(state['unmapped_proposals'])}\n")
                sys.stdout.write(f"  Run with --apply to write.\n")
                return 0
            apply_state(project_root, state)
            sys.stdout.write(f"✓ State written\n")
            sys.stdout.write(f"  Sprint: {state['current_sprint']}\n")
            return 0

        parser.print_help()
        return 1

    except PlannerStateError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1
    except FileNotFoundError as exc:
        sys.stderr.write(f"FILE NOT FOUND: {exc}\n")
        return 2