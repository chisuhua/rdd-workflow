"""rdd-doctor category: objective-structure.

Per add-objective-tracking change: structural invariants for objective files.
Read-only diagnostic; no file modification.

Invariants checked (mirrors _lib.objective.validate_objective):
  1. Frontmatter has all 9 required fields
  2. id matches pattern ^objective-[a-z0-9-]{0,63}$
  3. status in {active, deferred, completed, archived}
  4. priority in {P0, P1, P2}
  5. owner == "rdd-planner"
  6. manual_deps is a list
  7. Date fields (created/last_revised/review_by) are ISO format
  8. Required sections present: §1 §2 §3 §9 §10 §11
  9. Ledger kind values are in 5-value enum
  10. N/A format constraint: section 10 uses 'N/A — <reason>' (not plain 'N/A')
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity  # noqa: E402

from _lib.objective import parse_objective, validate_objective  # noqa: E402


def run(project_root: Path) -> List[Finding]:
    """Return structure findings for all objective files."""
    findings: List[Finding] = []
    obj_dir = project_root / ".rddf" / "roadmap" / "objectives"

    if not obj_dir.is_dir():
        return findings

    for f in sorted(obj_dir.glob("*.md")):
        if f.parent.name == "archive":
            continue

        try:
            data = parse_objective(f)
        except ValueError as e:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="objective-structure",
                file=str(f.relative_to(project_root)),
                line=None,
                snippet=f"parse error: {e}",
                fix_hint="fix frontmatter or regenerate via rddf roadmap add-objective",
            ))
            continue

        errors = validate_objective(data)
        for err in errors:
            severity = Severity.CRITICAL
            findings.append(Finding(
                severity=severity,
                category="objective-structure",
                file=str(f.relative_to(project_root)),
                line=None,
                snippet=err,
                fix_hint="fix per design.md constraints (schema v1)",
            ))

    return findings
