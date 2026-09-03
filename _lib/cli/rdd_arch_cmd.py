"""Stage 3 Change 4: rddf arch CLI subcommand.

Subcommands:
- rddf arch status       — one-line aggregate summary
- rddf arch handoff      — dump current .arch-handoff.json
- rddf arch feedback     — read-only view of .planner-feedback.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project-root", default=".", help="Project root directory")

    parser = argparse.ArgumentParser(prog="rddf arch", parents=[common])
    sub = parser.add_subparsers(dest="subcommand", required=True)

    sub.add_parser("status", help="One-line aggregate summary", parents=[common])
    sub.add_parser("handoff", help="Dump current .arch-handoff.json", parents=[common])
    sub.add_parser("feedback", help="Read-only view of planner feedback", parents=[common])

    return parser


def _cmd_status(project_root: Path) -> int:
    from _lib.rdd_arch_status import build_arch_status, format_status_line
    status = build_arch_status(str(project_root))
    sys.stdout.write(format_status_line(status) + "\n")
    return 0


def _cmd_handoff(project_root: Path) -> int:
    path = project_root / ".rddf" / "state" / ".arch-handoff.json"
    if not path.exists():
        sys.stdout.write("No .arch-handoff.json yet.\n")
        return 0
    try:
        with open(path) as f:
            sys.stdout.write(f.read())
            sys.stdout.write("\n")
    except OSError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1
    return 0


def _cmd_feedback(project_root: Path) -> int:
    from _lib.planner_feedback import read_planner_feedback
    data = read_planner_feedback(str(project_root))
    entries = data.get("feedbacks", [])
    summary = data.get("summary", {})
    if not entries:
        sys.stdout.write("No planner feedback recorded.\n")
        sys.stdout.write(f"Summary: {summary}\n")
        return 0
    sys.stdout.write("| ID | Kind | Severity | Status | Proposal | Stale |\n")
    sys.stdout.write("|----|------|----------|--------|----------|-------|\n")
    for e in entries:
        sys.stdout.write(
            f"| {e['feedback_id']} | {e['kind']} | {e['severity']} | "
            f"{e['status']} | {e['proposal']} | "
            f"{'yes' if e.get('stale') else 'no'} |\n"
        )
    sys.stdout.write(f"\nSummary: {summary}\n")
    return 0


def cmd_arch(args: List[str]) -> int:
    parser = _build_parser()
    ns = parser.parse_args(args)
    project_root = Path(ns.project_root).resolve()

    if ns.subcommand == "status":
        return _cmd_status(project_root)
    if ns.subcommand == "handoff":
        return _cmd_handoff(project_root)
    if ns.subcommand == "feedback":
        return _cmd_feedback(project_root)

    parser.print_help()
    return 1