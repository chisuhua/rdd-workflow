"""skills/guide-plan/scripts/plan_batch_fill.py — batch fill for design-pre-created changes.

Batch-generates ``design.md`` + ``tasks.md`` for one or more design-pre-created
changes from their ``proposal.md``, and moves their ``iteration.json`` status
from ``planned`` -> ``proposed``.

Design/tasks generation reuses the D2 mapping semantics of
``generate_full_proposal.py`` (same ``## Why / ## What Changes / ## Capabilities /
## Impact / ## Acceptance`` section conventions) so the produced ``design.md`` is
consistent with the canonical proposal format.

Contract (per plan-batch-fill-tool proposal):
  - Accept a change name list as positional args or ``--changes c1,c2,...``
  - Atomic write of ``iteration.json``
  - Idempotent — skip changes that already have a ``design.md``
  - Never modify ``_lib/iteration/store.py`` schema or ``generate_full_proposal.py``
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from skills._lib.core.atomic_write import atomic_write_json
from skills._lib.iteration import (
    add_or_update_change,
    load as load_iteration,
)

__all__ = [
    "BatchFillError",
    "BatchFillResult",
    "fill_changes",
    "fill_change",
    "main",
    "parse_changes_arg",
]

_SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)
_ACCEPTANCE_RE = re.compile(r"^## Acceptance\s*$(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
_CHECKBOX_RE = re.compile(r"^\s*-\s*\[[ xX]\]\s+(.+)$", re.MULTILINE)
_HEADER_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)

# (design.md H2 section, proposal.md section title)
_DESIGN_SECTION_MAP: tuple[tuple[str, str], ...] = (
    ("Context", "Why"),
    ("Goals", "What Changes"),
    ("Decisions", "Capabilities"),
    ("Risks", "Impact"),
)

# Canonical minimal design.md body for a change whose proposal lacks sections.
_FALLBACK_DESIGN = (
    "## Context\n\nTBD — see proposal.md ## Why.\n\n"
    "## Goals\n\nTBD — see proposal.md ## What Changes.\n\n"
    "## Decisions\n\nTBD — see proposal.md ## Capabilities.\n\n"
    "## Risks\n\nTBD — see proposal.md ## Impact.\n"
)


class BatchFillError(Exception):
    """Raised when a change cannot be batch-filled (invalid name / missing proposal)."""


@dataclass
class BatchFillResult:
    """Summary of a batch-fill run."""

    filled: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def parse_changes_arg(argv: list[str]) -> list[str]:
    """Extract the change name list from ``argv``.

    Accepts ``--changes c1,c2,...`` or bare positional args:
      ``plan_batch_fill.py one two three``
      ``plan_batch_fill.py --changes one,two,three``
    """
    changes: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--changes":
            if i + 1 >= len(argv):
                raise BatchFillError("--changes requires a comma-separated value")
            changes.extend(a for a in argv[i + 1].split(",") if a)
            i += 2
        elif arg == "--dry-run":
            i += 1
        elif arg.startswith("-"):
            raise BatchFillError(f"unknown option: {arg}")
        else:
            changes.append(arg)
            i += 1
    return changes


def _validate_change_name(name: str) -> None:
    """Reject path-traversal / empty change names before touching the filesystem."""
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise BatchFillError(f"invalid change name: {name!r}")


def _change_dir(project_root: Path, name: str) -> Path:
    _validate_change_name(name)
    return project_root / "openspec" / "changes" / name


def _extract_section(proposal_md: str, title: str) -> str:
    """Extract content under ``## <title>`` up to the next ``## ``. Returns '' if missing."""
    pattern = re.compile(
        rf"^## {re.escape(title)}\s*$(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(proposal_md)
    return m.group(1).strip() if m else ""


def _change_title(proposal_md: str, fallback: str) -> str:
    m = _HEADER_RE.search(proposal_md)
    return m.group(1).strip() if m else fallback


def _render_design(proposal_md: str, name: str) -> str:
    """Render design.md (Context/Goals/Decisions/Risks) from proposal sections."""
    missing = [sec for _, sec in _DESIGN_SECTION_MAP if not _extract_section(proposal_md, sec)]
    if missing:
        # Degrade gracefully: keep what we can, fall back to TBD for the rest.
        return _render_design_partial(proposal_md, name)
    lines = [f"# {_change_title(proposal_md, name)}"]
    for design_sec, proposal_sec in _DESIGN_SECTION_MAP:
        lines.append("")
        lines.append(f"## {design_sec}")
        lines.append("")
        lines.append(_extract_section(proposal_md, proposal_sec))
    return "\n".join(lines) + "\n"


def _render_design_partial(proposal_md: str, name: str) -> str:
    """Render a design.md that fills present sections and TBD-markers the rest."""
    lines = [f"# {_change_title(proposal_md, name)}"]
    for design_sec, proposal_sec in _DESIGN_SECTION_MAP:
        body = _extract_section(proposal_md, proposal_sec)
        if not body:
            body = f"TBD — see proposal.md ## {proposal_sec}."
        lines.append("")
        lines.append(f"## {design_sec}")
        lines.append("")
        lines.append(body)
    return "\n".join(lines) + "\n"


def _render_tasks(proposal_md: str, name: str) -> str:
    """Render tasks.md Implementation Tasks from the proposal's Acceptance checkboxes.

    If the proposal has no ``## Acceptance`` section or no checkboxes, returns a
    minimal tasks.md with an empty Implementation Tasks section.
    """
    acceptance = _extract_section(proposal_md, "Acceptance")
    checkboxes = _CHECKBOX_RE.findall(acceptance)
    title = _change_title(proposal_md, name)
    if not checkboxes:
        return f"# Tasks: {name}\n\n## Implementation Tasks\n"
    lines = [f"# Tasks: {name}", "", "## Implementation Tasks", ""]
    for i, item in enumerate(checkboxes, start=1):
        lines.append(f"- [ ] Task {i}: {item.strip()}")
    return "\n".join(lines) + "\n"


def fill_change(project_root: str, name: str, *, dry_run: bool = False) -> str:
    """Fill a single change, returning its outcome ('filled' | 'skipped').

    Raises:
        BatchFillError: invalid change name or missing proposal.md.
    """
    root = Path(project_root)
    change_dir = _change_dir(root, name)
    proposal_path = change_dir / "proposal.md"

    # Idempotent: skip changes that already have a design.md.
    design_path = change_dir / "design.md"
    if design_path.exists():
        return "skipped"

    if not proposal_path.is_file():
        raise BatchFillError(f"missing proposal.md for change: {name}")

    proposal_md = proposal_path.read_text(encoding="utf-8")
    if dry_run:
        return "filled"

    design_path.write_text(_render_design(proposal_md, name), encoding="utf-8")
    (change_dir / "tasks.md").write_text(_render_tasks(proposal_md, name), encoding="utf-8")

    # Move iteration.json status planned -> proposed (atomic, merge-safe).
    data = load_iteration(str(root))
    updated = add_or_update_change(data, name=name, status="proposed")
    atomic_write_json(root / ".rddf" / "state" / "iteration.json", updated)
    return "filled"


def fill_changes(project_root: str, names: list[str], *, dry_run: bool = False) -> BatchFillResult:
    """Batch-fill the given change names, returning a summary result.

    Invalid names / missing proposals are collected into ``result.failed`` rather
    than aborting the whole batch (so one bad entry doesn't block the other 8).
    """
    result = BatchFillResult()
    for name in names:
        try:
            outcome = fill_change(project_root, name, dry_run=dry_run)
        except BatchFillError:
            result.failed.append(name)
            continue
        if outcome == "skipped":
            result.skipped.append(name)
        else:
            result.filled.append(name)
    return result


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point. Returns process exit code (0 success, 2 error)."""
    argv = list(sys_argv() if argv is None else argv)
    changes = parse_changes_arg(argv)
    dry_run = "--dry-run" in argv
    if not changes:
        print("ERROR: no change names provided (positional args or --changes c1,c2,...)", file=sys.stderr)
        return 2
    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    result = fill_changes(project_root, changes, dry_run=dry_run)
    print(f"filled={result.filled} skipped={result.skipped} failed={result.failed}")
    if result.failed:
        print(f"ERROR: failed to fill: {result.failed}", file=sys.stderr)
        return 2
    return 0


def sys_argv() -> list[str]:
    """Indirection over sys.argv for testability."""
    import sys
    return sys.argv[1:]


if __name__ == "__main__":
    raise SystemExit(main())
