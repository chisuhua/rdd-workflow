"""Cat 2 — Loose check for TDD 5-step structure in .rddf/plans/*.md.

WARNING only. Loose matching: 5 step markers must be present, but does NOT
enforce specific phrasing beyond the canonical marker. False-positive risk
is real; tune on the real corpus during execute phase.

Scope (per fix-test-isolation-and-hygiene): only plans that can still matter
are reported. A plan is in scope when its change is not archived, or when the
plan is recent (last commit younger than the historical threshold). When the
plan's age cannot be determined it is checked — the conservative direction.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Set

from doctor_render import Finding, Severity


_STEP_MARKERS = [
    "Write the failing test",
    "Run test to verify it fails",
    "Write minimal implementation",
    "Run test to verify it passes",
    "Defer commit",
]

_PLAN_DIR_REL = Path(".rddf") / "plans"
_HISTORICAL_THRESHOLD_DAYS = 30
_GIT_LOG_TIMEOUT_SECONDS = 30
_GIT_TS_MARKER = "@@@"


def _active_changes(project_root: Path) -> Set[str]:
    """Names of changes that are not archived.

    Union of two signals, because either one alone drifts:

    1. ``.rddf/state/iteration.json`` ``changes[]`` with ``status != archived``
       (a gitignored runtime file — early worklines get wiped from it);
    2. unarchived ``openspec/changes/<name>/`` directories.

    Never raises: unreadable or malformed input just contributes nothing.
    """
    active: Set[str] = set()

    state_file = project_root / ".rddf" / "state" / "iteration.json"
    try:
        data = json.loads(state_file.read_text())
    except (OSError, ValueError):
        data = None
    if isinstance(data, dict):
        changes = data.get("changes")
        if isinstance(changes, list):
            for change in changes:
                if not isinstance(change, dict):
                    continue
                if change.get("status") == "archived":
                    continue
                name = change.get("name")
                if isinstance(name, str) and name:
                    active.add(name)

    changes_dir = project_root / "openspec" / "changes"
    if changes_dir.is_dir():
        for entry in changes_dir.iterdir():
            if entry.is_dir() and entry.name != "archive":
                active.add(entry.name)

    return active


def _git_last_commit_ts(project_root: Path) -> Dict[str, int] | None:
    """Map ``{plan file name: unix timestamp of its last commit}``.

    One single ``git log`` pass — calling it per file would mean 100+
    subprocesses. Returns ``None`` when git cannot answer (not a repo, git
    missing, timeout), which callers MUST read as "every plan is recent".
    """
    try:
        result = subprocess.run(
            [
                "git", "log", f"--format={_GIT_TS_MARKER}%ct", "--name-only",
                "--", _PLAN_DIR_REL.as_posix(),
            ],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=_GIT_LOG_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None

    stamps: Dict[str, int] = {}
    timestamp: int | None = None
    for line in result.stdout.splitlines():
        if line.startswith(_GIT_TS_MARKER):
            try:
                timestamp = int(line[len(_GIT_TS_MARKER):].strip())
            except ValueError:
                timestamp = None
            continue
        path = line.strip()
        if not path or timestamp is None:
            continue
        # git reports repo-relative paths; plan files are flat under
        # .rddf/plans/, so the basename identifies the plan uniquely.
        name = path.rsplit("/", 1)[-1]
        if name.endswith(".md"):
            previous = stamps.get(name)
            if previous is None or timestamp > previous:
                stamps[name] = timestamp
    return stamps


def _is_in_scope(plan_file: Path, active: Set[str],
                 stamps: Dict[str, int] | None, cutoff: float) -> bool:
    if plan_file.stem in active:
        return True
    if stamps is None:
        return True
    timestamp = stamps.get(plan_file.name)
    if timestamp is None:
        return True
    return timestamp >= cutoff


def run(project_root: Path | None = None) -> List[Finding]:
    """Run cat-2 against project_root."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    plans_dir = project_root / _PLAN_DIR_REL
    if not plans_dir.is_dir():
        return []

    active = _active_changes(project_root)
    stamps = _git_last_commit_ts(project_root)
    cutoff = time.time() - _HISTORICAL_THRESHOLD_DAYS * 24 * 60 * 60

    findings: List[Finding] = []
    for plan_file in sorted(plans_dir.glob("*.md")):
        if not _is_in_scope(plan_file, active, stamps, cutoff):
            continue
        text = plan_file.read_text()
        missing = [m for m in _STEP_MARKERS if m not in text]
        if missing:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="plan-tdd",
                file=str(plan_file),
                line=None,
                snippet=f"missing TDD step markers: {', '.join(missing)}",
                fix_hint="`execute` may misread steps without the canonical 5-step structure",
            ))
    return findings
