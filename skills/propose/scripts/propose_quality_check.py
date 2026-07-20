"""skills/propose/scripts/propose_quality_check.py - Quality checks for OpenSpec change proposals.

Plan B from the improve-change-quality initiative. Runs 5 structural
checks against a change's proposal.md / tasks.md / roadmap.md and
reports deficiencies as warnings (or errors when STRICT_PROPOSE_GATE=yes).

Usage:
    python3 -m skills.propose.scripts.propose_quality_check --change <name>
    python3 -m skills.propose.scripts.propose_quality_check --change <name> --strict

When STRICT_PROPOSE_GATE=yes env var is set, failures exit 1.
Default mode: print warnings, exit 0.

The 5 checks (each returns list[str] of warnings; empty = pass):
    1. check_proposal_length(proposal_path)   - min 500 chars (strips skeleton boilerplate)
    2. check_adr_references(proposal_path)    - must reference >=1 ADR (regex ADR-\\d{4})
    3. check_scope_sections(proposal_path)    - must have In Scope + Out of Scope
    4. check_roadmap_alignment(name, root)    - change must appear in roadmap.md
    5. check_tasks_completeness(tasks_path)   - tasks.md must have >=2 unchecked items

Design: see openspec/changes/add-propose-output-validation/design.md
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import List

# Minimum proposal length in chars (aligned with Plan D input-sources threshold).
MIN_PROPOSAL_LENGTH = 500

# Minimum number of unchecked tasks in tasks.md.
MIN_TASKS_COUNT = 2

# Regex patterns (compiled once at import).
_ADR_PATTERN = re.compile(r"ADR-\d{4}")
_TASK_PATTERN = re.compile(r"^\s*-\s*\[ \]", re.MULTILINE)

# Skeleton boilerplate markers written by create_skeleton_change.
# We strip these before measuring length so an unfilled skeleton is
# detected as short even if raw byte count exceeds the threshold.
_SKELETON_MARKERS = ("<skeleton motivation", "<file path")


def check_proposal_length(proposal_path: str) -> List[str]:
    """Check proposal.md is at least 500 chars of meaningful content.

    Strips skeleton boilerplate markers (`<skeleton motivation`, `<file path`)
    before measuring length, so an unfilled skeleton is detected as short
    even if the raw byte count exceeds 500.

    Returns list of warning strings (empty = pass).
    """
    warnings: List[str] = []
    if not os.path.isfile(proposal_path):
        warnings.append(f"proposal.md not found at {proposal_path}")
        return warnings
    with open(proposal_path, encoding="utf-8") as f:
        content = f.read()
    stripped = content
    for marker in _SKELETON_MARKERS:
        stripped = stripped.replace(marker, "")
    if len(stripped) < MIN_PROPOSAL_LENGTH:
        warnings.append(
            f"proposal.md too short: {len(stripped)} chars (min {MIN_PROPOSAL_LENGTH})"
        )
    return warnings


def check_adr_references(proposal_path: str) -> List[str]:
    """Check proposal.md references at least one ADR (regex ADR-\\d{4}).

    Returns list of warning strings (empty = pass).
    Returns empty list when the file is missing (missing-file warning is
    already emitted by check_proposal_length; we avoid double-reporting).
    """
    warnings: List[str] = []
    if not os.path.isfile(proposal_path):
        return warnings
    with open(proposal_path, encoding="utf-8") as f:
        content = f.read()
    if not _ADR_PATTERN.search(content):
        warnings.append("proposal.md references no ADR (must reference >=1 ADR)")
    return warnings


def check_scope_sections(proposal_path: str) -> List[str]:
    """Check proposal.md has In Scope and Out of Scope sections.

    Accepts both 'Out of Scope' and 'Out Scope' (shorthand) for the
    out-of-scope section. Case-sensitive substring match (proposals
    may use either `## In Scope` or `**In Scope:**` styling).

    Returns list of warning strings (empty = pass). May return up to 2
    warnings (one per missing section).
    """
    warnings: List[str] = []
    if not os.path.isfile(proposal_path):
        return warnings
    with open(proposal_path, encoding="utf-8") as f:
        content = f.read()
    if "In Scope" not in content:
        warnings.append("proposal.md missing 'In Scope' section")
    if "Out of Scope" not in content and "Out Scope" not in content:
        warnings.append("proposal.md missing 'Out of Scope' section")
    return warnings


def check_roadmap_alignment(name: str, project_root: str) -> List[str]:
    """Check the change name appears in roadmap.md.

    Uses substring match (change names commonly appear as `### name`
    headers or in tables). Returns soft warning when roadmap.md is
    missing (compat mode is valid).

    Returns list of warning strings (empty = pass).
    """
    warnings: List[str] = []
    roadmap_path = os.path.join(project_root, "roadmap.md")
    if not os.path.isfile(roadmap_path):
        warnings.append("roadmap.md not found, cannot verify alignment")
        return warnings
    with open(roadmap_path, encoding="utf-8") as f:
        content = f.read()
    if name not in content:
        warnings.append(
            f"change '{name}' not found in roadmap.md (may be misaligned)"
        )
    return warnings


def check_tasks_completeness(tasks_path: str) -> List[str]:
    """Check tasks.md has at least 2 unchecked task items.

    Matches standard markdown task list syntax `- [ ]` with leading
    whitespace tolerance. Checked items `- [x]` are NOT counted
    (they represent done work, not future work).

    Returns list of warning strings (empty = pass).
    """
    warnings: List[str] = []
    if not os.path.isfile(tasks_path):
        warnings.append(f"tasks.md not found at {tasks_path}")
        return warnings
    with open(tasks_path, encoding="utf-8") as f:
        content = f.read()
    tasks = _TASK_PATTERN.findall(content)
    if len(tasks) < MIN_TASKS_COUNT:
        warnings.append(
            f"tasks.md has only {len(tasks)} task(s) (min {MIN_TASKS_COUNT})"
        )
    return warnings


def run_all_checks(name: str, project_root: str) -> List[str]:
    """Run all 5 checks and return combined warnings list.

    Checks run in order: proposal_length -> adr_references ->
    scope_sections -> roadmap_alignment -> tasks_completeness.
    All checks always run (no short-circuit) so the caller sees the
    complete picture.
    """
    change_dir = os.path.join(project_root, "openspec", "changes", name)
    proposal_path = os.path.join(change_dir, "proposal.md")
    tasks_path = os.path.join(change_dir, "tasks.md")

    warnings: List[str] = []
    warnings.extend(check_proposal_length(proposal_path))
    warnings.extend(check_adr_references(proposal_path))
    warnings.extend(check_scope_sections(proposal_path))
    warnings.extend(check_roadmap_alignment(name, project_root))
    warnings.extend(check_tasks_completeness(tasks_path))
    return warnings


def main(argv: list[str] | None = None) -> List[str] | None:
    """CLI entry point.

    Args:
        argv: optional argv list (defaults to sys.argv[1:]).

    Returns:
        warnings list when in default mode (no sys.exit).
        In strict mode, calls sys.exit(1) on any warning (does not return).

    Behavior:
        - --change <name>: required, the change to check
        - --strict: optional flag, exit 1 on any warning
        - STRICT_PROPOSE_GATE=yes env var: same as --strict
        - --strict flag takes precedence over env var
    """
    parser = argparse.ArgumentParser(
        description="Propose output quality checker (Plan B)"
    )
    parser.add_argument("--change", required=True, help="Change name to check")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 on any warning (overrides STRICT_PROPOSE_GATE env var)",
    )
    args = parser.parse_args(argv)

    project_root = os.environ.get("PROJECT_ROOT", os.getcwd())
    strict = args.strict or os.environ.get("STRICT_PROPOSE_GATE") == "yes"

    warnings = run_all_checks(args.change, project_root)

    if warnings:
        print(f"⚠️  Quality warnings for '{args.change}':")
        for w in warnings:
            print(f"   - {w}")
        if strict:
            print("❌ STRICT_PROPOSE_GATE=yes: exiting with error")
            sys.exit(1)
        else:
            print("ℹ️  Set STRICT_PROPOSE_GATE=yes to upgrade warnings to errors")
    else:
        print(f"✅ '{args.change}' passes all quality checks")

    return warnings


if __name__ == "__main__":
    main()
