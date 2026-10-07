"""rdd-doctor category: roadmap-md-integrity (per add-roadmap-phases-and-md-integrity-category).

Read-only diagnostic that validates `.rddf/roadmap.md` markdown structure:
  B1. Phase Skeleton table has 5 columns (Phase / Theme / Status / Started / Done)
  B2. AUTO-INDEX has all 3 sub-segments (Phases / Features / Objectives)
  B3. Phases segment ↔ .rddf/roadmap/phases/*.md disk sync
  B4. ADR links in table cells resolve to existing docs/adr/*.md
  B5. (Advisory) Current Sprint block phase column ⊆ Phases segment
      (uses START_SENTINEL constant imported from _lib.roadmap_sprint,
       the single-writer per test_adr_index_gate.py invariant)

Severity: schema violation = CRITICAL; drift = CRITICAL; missing optional = WARNING.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity
from _lib.roadmap_md_integrity import (
    parse_main_doc_table,
    parse_auto_index_segments,
    validate_adr_links,
    validate_index_segment_sync,
)
from _lib.roadmap_sprint import START_SENTINEL as _AUTO_SPRINT_SENTINEL


_VALID_STATUSES = {"active", "deferred", "completed", "archived"}


def _check_table_schema(project_root: Path) -> List[Finding]:
    roadmap_path = project_root / ".rddf" / "roadmap.md"
    if not roadmap_path.is_file():
        return []
    text = roadmap_path.read_text(encoding="utf-8")
    if "## Phase Skeleton" not in text:
        return [Finding(
            severity=Severity.CRITICAL,
            category="roadmap-md-integrity.table-schema",
            file=str(roadmap_path),
            line=None,
            snippet="missing `## Phase Skeleton` section",
            fix_hint="add canonical 5-column Phase Skeleton table",
        )]
    rows = parse_main_doc_table(roadmap_path, text)
    if not rows and "## Phase Skeleton" in text:
        return [Finding(
            severity=Severity.CRITICAL,
            category="roadmap-md-integrity.table-schema",
            file=str(roadmap_path),
            line=None,
            snippet="Phase Skeleton table rows do not match 5-column schema (Phase / Theme / Status / Started / Done)",
            fix_hint="ensure each row has exactly 5 columns",
        )]
    findings: List[Finding] = []
    for pid, theme, status, started, done in rows:
        if status and status not in _VALID_STATUSES:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="roadmap-md-integrity.table-schema",
                file=str(roadmap_path),
                line=None,
                snippet=f"{pid}: invalid status '{status}' (expected: active|deferred|completed|archived)",
                fix_hint="set Status to a valid value",
            ))
    return findings


def _check_auto_index_segments(project_root: Path) -> List[Finding]:
    roadmap_path = project_root / ".rddf" / "roadmap.md"
    if not roadmap_path.is_file():
        return []
    text = roadmap_path.read_text(encoding="utf-8")
    segs = parse_auto_index_segments(text)
    findings: List[Finding] = []
    required = {"Phases", "Features", "Objectives"}
    missing = required - set(segs.keys())
    for name in sorted(missing):
        findings.append(Finding(
            severity=Severity.WARNING,
            category="roadmap-md-integrity.index-segment",
            file=str(roadmap_path),
            line=None,
            snippet=f"AUTO-INDEX missing required `### {name}` segment",
            fix_hint=f"add `### {name}` segment under AUTO-INDEX",
        ))
    return findings


def _check_index_drift(project_root: Path) -> List[Finding]:
    roadmap_path = project_root / ".rddf" / "roadmap.md"
    if not roadmap_path.is_file():
        return []
    text = roadmap_path.read_text(encoding="utf-8")
    segs = parse_auto_index_segments(text)
    findings: List[Finding] = []
    for d in validate_index_segment_sync(segs, project_root / ".rddf" / "roadmap"):
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="roadmap-md-integrity.index-sync",
            file=str(roadmap_path),
            line=None,
            snippet=d["snippet"],
            fix_hint=d["fix_hint"],
        ))
    return findings


def _check_adr_links(project_root: Path) -> List[Finding]:
    roadmap_path = project_root / ".rddf" / "roadmap.md"
    if not roadmap_path.is_file():
        return []
    text = roadmap_path.read_text(encoding="utf-8")
    adr_dir = project_root / "docs" / "adr"
    findings: List[Finding] = []
    for d in validate_adr_links(text, adr_dir):
        findings.append(Finding(
            severity=Severity.WARNING,
            category="roadmap-md-integrity.adr-links",
            file=str(roadmap_path),
            line=None,
            snippet=d["snippet"],
            fix_hint=d["fix_hint"],
        ))
    return findings


def _check_auto_sprint(project_root: Path) -> List[Finding]:
    roadmap_path = project_root / ".rddf" / "roadmap.md"
    if not roadmap_path.is_file():
        return []
    text = roadmap_path.read_text(encoding="utf-8")
    if _AUTO_SPRINT_SENTINEL not in text:
        return []  # absent is OK (template-only feature)
    segs = parse_auto_index_segments(text)
    valid_phases = segs.get("Phases", set())
    findings: List[Finding] = []
    after_sprint = text.split(_AUTO_SPRINT_SENTINEL, 1)[1]
    for line in after_sprint.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")]
        for cell in cells:
            if cell.startswith("phase-") and cell not in valid_phases:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category="roadmap-md-integrity.sprint-drift",
                    file=str(roadmap_path),
                    line=None,
                    snippet=f"Current Sprint references '{cell}' but not in AUTO-INDEX Phases segment",
                    fix_hint="add phase to AUTO-INDEX or remove from Current Sprint",
                ))
    return findings


def run(project_root: Path | None = None) -> List[Finding]:
    import os
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings: List[Finding] = []
    findings.extend(_check_table_schema(project_root))
    findings.extend(_check_auto_index_segments(project_root))
    findings.extend(_check_index_drift(project_root))
    findings.extend(_check_adr_links(project_root))
    findings.extend(_check_auto_sprint(project_root))
    return findings