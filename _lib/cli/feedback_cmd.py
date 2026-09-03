"""CLI dispatcher for `rddf feedback ...` subcommands.

Subcommands:
  add <proposal> --from X --kind Y --body Z [--ref-change C] [--dry-run]
  list <proposal>
  resolve <proposal> <feedback-id>
  show-schema
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from _lib.feedback_appender import (
    VALID_SOURCES,
    VALID_KINDS,
    FeedbackError,
    LoopExceededError,
    append_feedback,
)


_VALID_SOURCES_TUPLE = tuple(sorted(VALID_SOURCES))
_VALID_KINDS_TUPLE = tuple(sorted(VALID_KINDS))


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project-root", default=".", help="Project root (default: cwd)")

    parser = argparse.ArgumentParser(
        prog="rddf feedback",
        description="Append feedback to .rddf/improvements/*.md files (single writer per ADR-0037).",
        parents=[common],
    )

    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_add = sub.add_parser("add", help="Append feedback entry", parents=[common])
    p_add.add_argument("proposal", help="Proposal name (file basename without .md)")
    p_add.add_argument("--from", dest="source", required=True, choices=_VALID_SOURCES_TUPLE)
    p_add.add_argument("--kind", required=True, choices=_VALID_KINDS_TUPLE)
    p_add.add_argument("--body", required=True, help="Body text (or @file)")
    p_add.add_argument("--ref-change", dest="ref_change", default=None)
    p_add.add_argument("--dry-run", action="store_true")

    p_list = sub.add_parser("list", help="List feedback entries", parents=[common])
    p_list.add_argument("proposal")

    p_resolve = sub.add_parser("resolve", help="Mark entry resolved", parents=[common])
    p_resolve.add_argument("proposal")
    p_resolve.add_argument("feedback_id")

    sub.add_parser("show-schema", help="Print feedback entry JSON schema to stdout", parents=[common])

    return parser


def _resolve_body(body_arg: str) -> str:
    """If body_arg starts with @, read from file; else return as-is."""
    if body_arg.startswith("@"):
        return Path(body_arg[1:]).read_text(encoding="utf-8")
    return body_arg


def _find_improvement(project_root: Path, proposal: str) -> Path:
    """Locate .rddf/improvements/<proposal>.md; raise FeedbackError if missing."""
    target = project_root / ".rddf" / "improvements" / f"{proposal}.md"
    if not target.exists():
        raise FeedbackError(f"Improvement file not found: {target}")
    return target


def cmd_feedback(args: List[str]) -> int:
    """Main entry: parse args, dispatch to sub-handler, return exit code."""
    parser = _build_parser()
    ns = parser.parse_args(args)

    project_root = Path(ns.project_root).resolve()

    try:
        if ns.subcommand == "show-schema":
            schema_path = Path(__file__).parent.parent / "schemas" / "feedback_entry_schema.json"
            sys.stdout.write(schema_path.read_text())
            return 0

        if ns.subcommand == "add":
            target = _find_improvement(project_root, ns.proposal)
            body = _resolve_body(ns.body)
            if ns.dry_run:
                if ns.source not in VALID_SOURCES:
                    raise FeedbackError(f"Invalid source: {ns.source}")
                if ns.kind not in VALID_KINDS:
                    raise FeedbackError(f"Invalid kind: {ns.kind}")
                if not (1 <= len(body) <= 10000):
                    raise FeedbackError(f"Body length {len(body)} out of range")
                sys.stdout.write(f"DRY-RUN: would append feedback to {target}\n")
                return 0
            feedback_id = append_feedback(
                target_path=str(target),
                source=ns.source,
                kind=ns.kind,
                body=body,
                ref_change=ns.ref_change,
            )
            sys.stdout.write(
                f"✓ Feedback appended: {feedback_id}\n"
                f"  File: {target}\n"
                f"  Source: {ns.source}\n"
                f"  Kind: {ns.kind}\n"
            )
            return 0

        if ns.subcommand == "list":
            target = _find_improvement(project_root, ns.proposal)
            text = target.read_text(encoding="utf-8")
            sys.stdout.write(text)
            return 0

        if ns.subcommand == "resolve":
            target = _find_improvement(project_root, ns.proposal)
            try:
                from _lib.feedback_appender import resolve_feedback as _resolve_feedback
                _resolve_feedback(target_path=str(target), feedback_id=ns.feedback_id)
            except FeedbackError as exc:
                sys.stderr.write(f"ERROR: {exc}\n")
                return 1
            sys.stdout.write(
                f"✓ Resolved: {ns.feedback_id}\n  File: {target}\n"
            )
            return 0

        parser.print_help()
        return 1

    except LoopExceededError as exc:
        sys.stderr.write(f"LOOP EXCEEDED: {exc}\n")
        return 1
    except FeedbackError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1
    except FileNotFoundError as exc:
        sys.stderr.write(f"FILE NOT FOUND: {exc}\n")
        return 2