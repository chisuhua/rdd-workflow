"""rdd-doctor category: objective-lifecycle.

Per add-objective-tracking change: 90-day grace check via review_by field.
Read-only diagnostic; no file modification.

Invariants checked:
  1. Each `.rddf/roadmap/objectives/*.md` (non-archive) parses without error
  2. Status is one of {active, deferred, completed, archived}
  3. review_by is present and in ISO date format
  4. If review_by < today AND status in (active, deferred) → WARNING (grace exceeded)
  5. If status=completed and review_by very old → INFO (suggest archive)

No file modification (READ-ONLY). Uses `_lib.objective.parse_objective` and
`_lib.objective.grace_period_exceeded`.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from typing import List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity  # noqa: E402

from _lib.objective import (  # noqa: E402
    STATUS_ENUM,
    grace_period_exceeded,
    parse_objective,
)


def run(project_root: Path) -> List[Finding]:
    """Return lifecycle findings for all objective files.

    Exit codes (per add-objective-tracking acceptance):
      - 0: no findings (all objectives within grace)
      - 1: WARNING findings only (grace exceeded, planner must decide)
      - 2: CRITICAL findings present (malformed file or invalid status)
    """
    findings: List[Finding] = []
    obj_dir = project_root / ".rddf" / "roadmap" / "objectives"

    if not obj_dir.is_dir():
        return findings  # no objectives defined yet → INFO (not CRITICAL)

    for f in sorted(obj_dir.glob("*.md")):
        if f.parent.name == "archive":
            continue

        try:
            data = parse_objective(f)
        except ValueError as e:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="objective-lifecycle",
                file=str(f.relative_to(project_root)),
                line=None,
                snippet=f"parse error: {e}",
                fix_hint="fix frontmatter or regenerate via rddf roadmap add-objective",
            ))
            continue

        fm = data["frontmatter"]
        status = fm.get("status")

        if status not in STATUS_ENUM:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="objective-lifecycle",
                file=str(f.relative_to(project_root)),
                line=None,
                snippet=f"invalid status: {status!r}",
                fix_hint=f"set status to one of {sorted(STATUS_ENUM)}",
            ))
            continue

        review_by = fm.get("review_by")
        if not review_by or not re.match(r"^\d{4}-\d{2}-\d{2}$", str(review_by)):
            findings.append(Finding(
                severity=Severity.WARNING,
                category="objective-lifecycle",
                file=str(f.relative_to(project_root)),
                line=None,
                snippet=f"missing or non-ISO review_by: {review_by!r}",
                fix_hint="set review_by to ISO date (YYYY-MM-DD), default = created + 90 days",
            ))
            continue

        if grace_period_exceeded(data):
            findings.append(Finding(
                severity=Severity.WARNING,
                category="objective-lifecycle",
                file=str(f.relative_to(project_root)),
                line=None,
                snippet=f"grace exceeded: review_by={review_by}, status={status}",
                fix_hint="planner must call revise-objective or archive-objective",
            ))

    return findings
