"""CLI dispatcher for `rddf planner ...` subcommands.

Stage 2 MVP + Stage 2.5 P0-3 attach:
  status                       read-only sprint snapshot
  sync [--apply] [--dry-run]   default --dry-run; --apply writes state
  attach <proposal> --project-id X --phase Y [--theme Z]
                               validated single-file proposal attach
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from _lib.planner_attach import AttachError
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

    p_attach = sub.add_parser("attach", help="Attach proposal to roadmap project/phase",
                              parents=[common])
    p_attach.add_argument("proposal", help="Proposal name (basename without .md)")
    p_attach.add_argument("--project-id", required=True,
                          help="project_id must match a Theme value in ## Phase Skeleton")
    p_attach.add_argument("--phase", required=True,
                          help="phase must match a Phase value or fragment id")
    p_attach.add_argument("--theme", default=None,
                          help="Optional theme string stored in roadmap_ref.theme")
    sub.add_parser("diff", help="Compare stored vs computed state", parents=[common])

    p_audit = sub.add_parser("audit", help="List unmapped proposals (read-only)", parents=[common])
    p_audit.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")

    p_attach.add_argument("--overwrite", action="store_true",
                          help="Replace an existing divergent roadmap_ref")

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
            from _lib.planner_sync import apply_state_with_warnings as _apply_state_with_warn
            _apply_state_with_warn(project_root, state)
            sys.stdout.write(f"✓ State written\n")
            sys.stdout.write(f"  Sprint: {state['current_sprint']}\n")
            return 0

        if ns.subcommand == "attach":
            from _lib.planner_attach import attach_proposal
            try:
                attach_proposal(
                    project_root=project_root,
                    proposal=ns.proposal,
                    project_id=ns.project_id,
                    phase=ns.phase,
                    theme=ns.theme,
                    overwrite=ns.overwrite,
                )
            except AttachError as exc:
                sys.stderr.write(f"ERROR: {exc}\n")
                return 1
            sys.stdout.write(f"✓ Attached: {ns.proposal} -> {ns.project_id}/{ns.phase}\n")
            return 0

        if ns.subcommand == "diff":
            from _lib.planner_sync import diff_state
            diff = diff_state(project_root)
            if not diff["has_baseline"]:
                sys.stdout.write("No baseline state on disk; nothing to diff.\n")
                return 0
            added = diff["unmapped_diff"]["added"]
            removed = diff["unmapped_diff"]["removed"]
            proj = diff["projects_diff"]
            if not added and not removed and not proj:
                sys.stdout.write("Stored and computed state agree.\n")
                return 0
            if added:
                sys.stdout.write(f"Unmapped added: {', '.join(added)}\n")
            if removed:
                sys.stdout.write(f"Unmapped removed: {', '.join(removed)}\n")
            for pid, fields in proj.items():
                diffs = ", ".join(f"{k}: {v[0]} -> {v[1]}" for k, v in fields.items())
                sys.stdout.write(f"{pid}: {diffs}\n")
            return 1

        if ns.subcommand == "audit":
            from _lib.planner_audit import build_audit_rows, render_markdown
            rows = build_audit_rows(project_root)
            if ns.json:
                import json as _json
                from dataclasses import asdict
                sys.stdout.write(_json.dumps([asdict(r) for r in rows], indent=2, ensure_ascii=False))
                sys.stdout.write("\n")
            else:
                sys.stdout.write(render_markdown(rows))
            return 0

        parser.print_help()
        return 1

    except PlannerStateError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1
    except FileNotFoundError as exc:
        sys.stderr.write(f"FILE NOT FOUND: {exc}\n")
        return 2