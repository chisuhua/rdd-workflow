"""rdd-doctor category: roadmap-phases (per add-roadmap-phases-and-md-integrity-category).

Read-only diagnostic that validates `.rddf/roadmap/phases/*.md` artifacts:
  A1. frontmatter has required fields (id, kind, status, phase_refs, 主题)
  A2. AUTO-INDEX Phases segment in `.rddf/roadmap.md` matches disk files
  A3. phases referenced in `.rddf/roadmap.md` Phase Skeleton table exist on disk
  A4. phase_refs should be [] (phases don't reference other phases)

Severity policy mirrors roadmap-feature: missing `status` is CRITICAL;
other missing fields are WARNING; disk↔AUTO-INDEX drift is CRITICAL.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity
from _lib.roadmap_state import load_fragments
from _lib.roadmap_validate import _extract_main_doc_phases


_REQUIRED_FIELDS = ("id", "kind", "status", "phase_refs", "主题")
_AUTO_INDEX_SENTINEL = "<!-- AUTO-INDEX -->"
_PHASE_LINE = re.compile(r"-\s*`(phase-\d+(?:\.\d+)?)`\s*—")


def _check_frontmatter(project_root: Path) -> List[Finding]:
    findings: List[Finding] = []
    fragments = load_fragments(str(project_root / ".rddf" / "roadmap"))
    for phase in [f for f in fragments if f.kind == "phase"]:
        try:
            fm_text = Path(phase.file_path).read_text(encoding="utf-8").split("---", 2)[1]
        except (OSError, UnicodeDecodeError, IndexError):
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category="roadmap-phases.frontmatter",
                file=phase.file_path,
                line=None,
                snippet=f"{phase.id}: malformed frontmatter (no /---)",
                fix_hint="re-emit phase frontmatter per Phase 1 template",
            ))
            continue
        present_keys = set()
        for line in fm_text.splitlines():
            if ":" in line and not line.startswith(" ") and not line.startswith("#"):
                present_keys.add(line.split(":", 1)[0].strip())
        for field in _REQUIRED_FIELDS:
            if field not in present_keys:
                sev = Severity.CRITICAL if field == "status" else Severity.WARNING
                findings.append(Finding(
                    severity=sev,
                    category="roadmap-phases.frontmatter",
                    file=phase.file_path,
                    line=None,
                    snippet=f"{phase.id}: missing required field '{field}'",
                    fix_hint=f"add '{field}: <value>' to frontmatter",
                ))
    return findings


def _check_auto_index(project_root: Path) -> List[Finding]:
    roadmap_path = project_root / ".rddf" / "roadmap.md"
    if not roadmap_path.is_file():
        return []
    text = roadmap_path.read_text(encoding="utf-8")
    if _AUTO_INDEX_SENTINEL not in text:
        return []
    after = text.split(_AUTO_INDEX_SENTINEL, 1)[1]
    m = re.search(r"### Phases\n(.*?)(?=\n### |\n## |\Z)", after, re.DOTALL)
    indexed: set[str] = set()
    if m:
        for line in m.group(1).splitlines():
            mm = _PHASE_LINE.match(line.strip())
            if mm:
                indexed.add(mm.group(1))
    fragments = load_fragments(str(project_root / ".rddf" / "roadmap"))
    disk_ids = {f.id for f in fragments if f.kind == "phase"}
    findings: List[Finding] = []
    for pid in sorted(disk_ids - indexed):
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="roadmap-phases.index-drift",
            file=str(roadmap_path),
            line=None,
            snippet=f"{pid}: disk phase exists but missing from .rddf/roadmap.md AUTO-INDEX Phases",
            fix_hint="rddf roadmap --reindex or manually add to AUTO-INDEX",
        ))
    for pid in sorted(indexed - disk_ids):
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="roadmap-phases.index-drift",
            file=str(roadmap_path),
            line=None,
            snippet=f"AUTO-INDEX Phases references '{pid}' but no phase file exists",
            fix_hint="remove stale entry from AUTO-INDEX or recreate phase file",
        ))
    return findings


def _check_main_doc_consistency(project_root: Path) -> List[Finding]:
    main_doc_ids = _extract_main_doc_phases(project_root / ".rddf" / "roadmap.md")
    if not main_doc_ids:
        return []
    fragments = load_fragments(str(project_root / ".rddf" / "roadmap"))
    disk_ids = {f.id for f in fragments if f.kind == "phase"}
    findings: List[Finding] = []
    for pid in sorted(main_doc_ids - disk_ids):
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="roadmap-phases.main-doc-missing",
            file=str(project_root / ".rddf" / "roadmap.md"),
            line=None,
            snippet=f"{pid}: referenced in main doc Phase Skeleton but no phase file",
            fix_hint=f"create .rddf/roadmap/phases/{pid}.md or remove from main doc",
        ))
    return findings


def _check_phase_refs_self_ref(project_root: Path) -> List[Finding]:
    findings: List[Finding] = []
    fragments = load_fragments(str(project_root / ".rddf" / "roadmap"))
    for phase in [f for f in fragments if f.kind == "phase"]:
        if phase.phase_refs:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="roadmap-phases.ref-misuse",
                file=phase.file_path,
                line=None,
                snippet=f"{phase.id}: phase_refs should be empty (phases don't reference phases); got {phase.phase_refs}",
                fix_hint="set phase_refs: [] in frontmatter",
            ))
    return findings


def run(project_root: Path | None = None) -> List[Finding]:
    if project_root is None:
        import os
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings: List[Finding] = []
    findings.extend(_check_frontmatter(project_root))
    findings.extend(_check_auto_index(project_root))
    findings.extend(_check_main_doc_consistency(project_root))
    findings.extend(_check_phase_refs_self_ref(project_root))
    return findings