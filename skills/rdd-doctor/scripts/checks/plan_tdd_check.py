"""Cat 2 — Loose check for TDD 5-step structure in .rddf/plans/*.md.

WARNING only. Loose matching: 5 step markers must be present, but does NOT
enforce specific phrasing beyond the canonical marker. False-positive risk
is real; tune on the real corpus during execute phase.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity


_STEP_MARKERS = [
    "Write the failing test",
    "Run test to verify it fails",
    "Write minimal implementation",
    "Run test to verify it passes",
    "Defer commit",
]


def run(project_root: Path | None = None) -> List[Finding]:
    """Run cat-2 against project_root."""
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    plans_dir = project_root / ".rddf" / "plans"
    if not plans_dir.is_dir():
        return []

    findings: List[Finding] = []
    for plan_file in sorted(plans_dir.glob("*.md")):
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