"""Check all .rddf/improvements/*.md files for valid YAML frontmatter.

Files MUST start with '---' on line 1 (per `_lib/planner_attach.py` L158-160).
Missing frontmatter means `rddf planner attach` will fail.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from doctor_render import Finding, Severity


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))

    impr_dir = project_root / ".rddf" / "improvements"
    if not impr_dir.is_dir():
        return []

    findings: List[Finding] = []
    for f in sorted(impr_dir.glob("*.md")):
        if not f.is_file():
            continue
        try:
            first_line = f.read_text(encoding="utf-8").split("\n", 1)[0]
        except (OSError, UnicodeDecodeError):
            findings.append(Finding(
                severity=Severity.WARNING,
                category="improvement-frontmatter-consistency",
                file=str(f.relative_to(project_root)),
                line=None,
                snippet=f"unreadable file: {f.name}",
                fix_hint="check file permissions and encoding",
            ))
            continue

        if first_line.strip() != "---":
            findings.append(Finding(
                severity=Severity.WARNING,
                category="improvement-frontmatter-consistency",
                file=str(f.relative_to(project_root)),
                line=1,
                snippet=f"missing frontmatter delimiters — first line is {first_line!r}, expected '---'",
                fix_hint=f"run: python3 -m _lib.cli.migrate_improvement_frontmatter --project-root {project_root}",
            ))

    return findings