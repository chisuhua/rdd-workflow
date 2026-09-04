"""CLI dispatcher for `rddf planner ...` subcommands.

Stage 2 MVP + Stage 2.5 P0-3 attach:
  status                       read-only sprint snapshot
  sync [--apply] [--dry-run]   default --dry-run; --apply writes state
  attach <proposal> --project-id X --phase Y [--theme Z]
                               validated single-file proposal attach
"""
from __future__ import annotations

import argparse
import os
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

    p_adv = sub.add_parser("advance-sprint", help="Close current sprint and advance to next", parents=[common])
    p_adv.add_argument("--to-sprint", default=None, help="Target sprint ID (default: next month)")
    p_adv.add_argument("--force", action="store_true", help="Allow backward/same sprint advancement")
    p_adv.add_argument("--dry-run", action="store_true", help="Preview advancement without writing")

    p_hist = sub.add_parser("history", help="Show or prune sprint history", parents=[common])
    p_hist.add_argument("--last", type=int, default=None, help="Show last N sprints")
    p_hist.add_argument("--since", default=None, help="Show sprints since YYYY-MM")
    p_hist.add_argument("--json", action="store_true", help="Output JSON format")
    p_hist.add_argument("--prune-keep", type=int, default=None, help="Prune older sprints keeping N latest")
    p_hist.add_argument("--apply", action="store_true", help="Apply prune modification (default dry-run)")

    p_audit = sub.add_parser("audit", help="List unmapped proposals (read-only)", parents=[common])
    p_audit.add_argument("--json", action="store_true", help="Output JSON instead of Markdown")

    p_fb = sub.add_parser("feedback", help="View or update planner feedback (persistent review tasks)", parents=[common])
    p_fb.add_argument("--status", choices=["open", "acknowledged", "resolved", "dismissed"],
                      help="Filter by lifecycle status")
    p_fb.add_argument("--kind", choices=["unmapped_proposal", "coverage_gap", "adr_drift", "roadmap_staleness"],
                      help="Filter by feedback kind")
    p_fb.add_argument("--json", action="store_true", help="Output JSON format")
    p_fb.add_argument("--recompute", action="store_true", help="Force recompute from filesystem")
    p_fb.add_argument("--acknowledge", default=None, metavar="FEEDBACK_ID",
                      help="Transition feedback to acknowledged status")
    p_fb.add_argument("--resolve", default=None, metavar="FEEDBACK_ID",
                      help="Transition feedback to resolved status")
    p_fb.add_argument("--dismiss", default=None, metavar="FEEDBACK_ID",
                      help="Transition feedback to dismissed status")
    p_fb.add_argument("--prune-resolved", action="store_true",
                      help="Remove resolved/dismissed entries")

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
            if not os.environ.get("SKIP_AUTO_PLANNER_FEEDBACK"):
                from _lib.planner_feedback import safe_recompute_planner_feedback
                safe_recompute_planner_feedback(str(project_root))
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

        if ns.subcommand == "advance-sprint":
            from _lib.planner_sync import advance_sprint, SyncError
            try:
                res = advance_sprint(
                    project_root,
                    to_sprint=ns.to_sprint,
                    force=ns.force,
                    dry_run=ns.dry_run,
                )
            except SyncError as exc:
                sys.stderr.write(f"ERROR: {exc}\n")
                return 1

            if res.get("dry_run"):
                sys.stdout.write(f"DRY-RUN: would advance {res['old_sprint']} -> {res['new_sprint']}\n")
            else:
                sys.stdout.write(f"✓ Sprint advanced: {res['old_sprint']} -> {res['new_sprint']}\n")
            return 0

        if ns.subcommand == "history":
            from _lib.planner_history import read_history, prune_history
            from dataclasses import asdict

            if ns.prune_keep is not None:
                dry_run = not ns.apply
                count = prune_history(project_root, keep=ns.prune_keep, dry_run=dry_run)
                if dry_run:
                    sys.stdout.write(f"DRY-RUN: would prune {count} historical sprint(s) (keeping {ns.prune_keep})\n")
                else:
                    sys.stdout.write(f"✓ Pruned {count} historical sprint(s)\n")
                return 0

            entries, corrupt_count = read_history(project_root)
            if corrupt_count > 0:
                sys.stderr.write(f"WARNING: skipped {corrupt_count} corrupted history record(s)\n")

            if ns.since:
                entries = [e for e in entries if e.sprint >= ns.since]
            if ns.last is not None and ns.last >= 0:
                entries = entries[-ns.last:]

            if not entries:
                sys.stdout.write("No sprint history recorded.\n")
                return 0

            if ns.json:
                import json as _json
                sys.stdout.write(_json.dumps([asdict(e) for e in entries], indent=2, ensure_ascii=False) + "\n")
            else:
                sys.stdout.write("| Sprint | Started | Closed | Active Projects |\n")
                sys.stdout.write("|--------|---------|--------|-----------------|\n")
                for e in entries:
                    active_count = len(e.snapshot.get("active_projects") or [])
                    started = e.started_at[:10] if len(e.started_at) >= 10 else e.started_at
                    closed = e.closed_at[:10] if len(e.closed_at) >= 10 else e.closed_at
                    sys.stdout.write(f"| {e.sprint} | {started} | {closed} | {active_count} |\n")
            return 0

        if ns.subcommand == "feedback":
            from _lib.planner_feedback import (
                acknowledge_feedback,
                compute_planner_feedback,
                dismiss_feedback,
                prune_resolved_feedback,
                read_planner_feedback,
                resolve_feedback,
                write_planner_feedback,
            )
            import json as _json

            if ns.recompute:
                data = compute_planner_feedback(str(project_root))
                write_planner_feedback(str(project_root), data)
                sys.stdout.write(f"✓ Recomputed {len(data['feedbacks'])} feedback entry(ies)\n")
                return 0

            if ns.prune_resolved:
                count = prune_resolved_feedback(str(project_root))
                sys.stdout.write(f"✓ Pruned {count} resolved/dismissed feedback entry(ies)\n")
                return 0

            if ns.acknowledge:
                if not acknowledge_feedback(str(project_root), ns.acknowledge):
                    sys.stderr.write(f"ERROR: feedback_id not found: {ns.acknowledge}\n")
                    return 1
                sys.stdout.write(f"✓ Acknowledged: {ns.acknowledge}\n")
                return 0

            if ns.resolve:
                if not resolve_feedback(str(project_root), ns.resolve):
                    sys.stderr.write(f"ERROR: feedback_id not found: {ns.resolve}\n")
                    return 1
                sys.stdout.write(f"✓ Resolved: {ns.resolve}\n")
                return 0

            if ns.dismiss:
                if not dismiss_feedback(str(project_root), ns.dismiss):
                    sys.stderr.write(f"ERROR: feedback_id not found: {ns.dismiss}\n")
                    return 1
                sys.stdout.write(f"✓ Dismissed: {ns.dismiss}\n")
                return 0

            data = read_planner_feedback(str(project_root))
            entries = data.get("feedbacks", [])

            if ns.status:
                entries = [e for e in entries if e.get("status") == ns.status]
            if ns.kind:
                entries = [e for e in entries if e.get("kind") == ns.kind]

            summary = data.get("summary", {})
            if not entries:
                sys.stdout.write("No active planner feedback.\n")
                if summary.get("open_critical", 0) == 0 and summary.get("open_warning", 0) == 0:
                    pass
                return 0

            if ns.json:
                sys.stdout.write(_json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
            else:
                sys.stdout.write("| ID | Kind | Severity | Status | Proposal | Stale |\n")
                sys.stdout.write("|----|------|----------|--------|----------|-------|\n")
                for e in entries:
                    sys.stdout.write(
                        f"| {e['feedback_id']} | {e['kind']} | {e['severity']} | "
                        f"{e['status']} | {e['proposal']} | "
                        f"{'yes' if e.get('stale') else 'no'} |\n"
                    )
            return 0

        parser.print_help()
        return 1

    except PlannerStateError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1
    except FileNotFoundError as exc:
        sys.stderr.write(f"FILE NOT FOUND: {exc}\n")
        return 2