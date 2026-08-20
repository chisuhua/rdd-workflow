"""rdd-doctor category: roadmap-refs (AC-2.3, AC-2.10).

Read-only diagnostic that calls validate_fragment_refs (8 rules R1-R8) and
converts the ValidationError list to rdd-doctor Finding objects.

Per AC-2.10: doctor must remain READ-ONLY — this checker must NOT modify any
tracked or gitignored files. Only reads `.rddf/roadmap/` + `.rddf/roadmap.md`.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

# Allow importing _lib.roadmap_validate (canonical project-root module)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity
from _lib.roadmap_validate import validate_fragment_refs


_SEVERITY_MAP = {
    "CRITICAL": Severity.CRITICAL,
    "WARNING": Severity.WARNING,
    "INFO": Severity.INFO,
}


def run(project_root: str) -> List[Finding]:
    """Run validate_fragment_refs and convert results to doctor Finding list.

    Args:
        project_root: Project root (typically from RDDF_PROJECT_ROOT env var).

    Returns:
        List of Finding objects, one per ValidationError. Empty list = no issues.
    """
    errors = validate_fragment_refs(project_root)
    findings: List[Finding] = []
    for e in errors:
        findings.append(
            Finding(
                severity=_SEVERITY_MAP.get(e.severity, Severity.WARNING),
                category=f"roadmap-refs.{e.rule}",
                file=f".rddf/roadmap/{e.fragment_id}",
                line=None,
                snippet=e.fragment_id,
                fix_hint=e.message,
            )
        )
    return findings
