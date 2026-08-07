"""Cat 5 — Validate openspec/changes/*/tasks.md checkbox state.

v1 intentionally does NOT cross-check with `openspec status --json` because:
1. openspec CLI v1.4.1 requires `schema:` field in .openspec.yaml (currently
   approve_proposal.sh does not write it)
2. `isComplete` is derived from artifact existence, not checkbox progress —
   making any cross-check vacuous even when CLI works

Degraded path: emit INFO finding when `openspec` is not on $PATH. This is
observability, not a failure (exit 3 reserved for genuine exceptions).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity


_CHECKBOX_PATTERN_OPEN = "- [ ]"
_CHECKBOX_PATTERN_DONE = "- [x]"


def _openspec_available() -> bool:
    return shutil.which("openspec") is not None


def run(project_root: Path | None = None) -> List[Finding]:
    """Run cat-5 against project_root."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    changes_root = project_root / "openspec" / "changes"
    if not changes_root.is_dir():
        return []

    findings: List[Finding] = []

    if not _openspec_available():
        findings.append(Finding(
            severity=Severity.INFO,
            category="tasks-checkbox",
            file="(global)",
            line=None,
            snippet="openspec status unavailable, skipping cross-check",
            fix_hint=(
                "install openspec CLI for v2 to enable status cross-check; "
                "v1 cat-5 runs without it"
            ),
        ))

    for change_dir in sorted(changes_root.iterdir()):
        if not change_dir.is_dir() or change_dir.name == "archive":
            continue
        tasks = change_dir / "tasks.md"
        if not tasks.is_file():
            findings.append(Finding(
                severity=Severity.WARNING,
                category="tasks-checkbox",
                file=str(tasks),
                line=None,
                snippet="tasks.md missing for active change",
                fix_hint="run guide-plan fill to generate tasks.md",
            ))
            continue
        text = tasks.read_text()
        open_count = text.count(_CHECKBOX_PATTERN_OPEN)
        done_count = text.count(_CHECKBOX_PATTERN_DONE)
        total = open_count + done_count
        if total == 0:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="tasks-checkbox",
                file=str(tasks),
                line=None,
                snippet="checkbox count = 0 but change is active",
                fix_hint="add task checkboxes; `execute` cannot track progress without them",
            ))
    return findings