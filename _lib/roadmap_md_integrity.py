"""Pure parsing helpers for `.rddf/roadmap.md` integrity checks.

Public functions:
    parse_main_doc_table(path, text) -> list[tuple]
    parse_auto_index_segments(text)   -> dict[str, set[str]]
    validate_adr_links(text, adr_docs_dir) -> list[dict]
    validate_index_segment_sync(segs, roadmap_root) -> list[dict]

All helpers are READ-ONLY and pure (no subprocess, no file writes).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


_PHASE_ROW_RE = re.compile(
    r"\|\s*(phase-\d+(?:\.\d+)?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$"
)
_ADR_LINK_RE = re.compile(r"\[ADR-(\d{4})\]\((?:\.\./)+(?:\./)?docs/adr/(ADR-\d{4}-[\w\-]+\.md)\)")
_AUTO_INDEX_SENTINEL = "<!-- AUTO-INDEX -->"
_SEGMENT_HEADER_RE = re.compile(r"^###\s+([A-Za-z][A-Za-z0-9_-]*)\s*$")
_BULLET_ID_RE = re.compile(r"-\s*`([\w\-]+)`\s*—")


def parse_main_doc_table(path: Path, text: str) -> List[Tuple[str, str, str, str, str]]:
    """Parse rows under `## Phase Skeleton` table.

    Returns list of 5-tuples (phase_id, theme, status, started, done).
    Only rows matching the canonical 5-column schema are returned;
    bad-column rows are silently skipped (caller emits WARNING).
    """
    rows: List[Tuple[str, str, str, str, str]] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## Phase Skeleton"):
            in_section = True
            continue
        if in_section and line.startswith("## ") and not line.startswith("## Phase Skeleton"):
            break
        if not in_section:
            continue
        m = _PHASE_ROW_RE.match(line)
        if m:
            g = m.groups()
            rows.append((g[0], g[1], g[2], g[3], g[4]))
    return rows


def parse_auto_index_segments(text: str) -> Dict[str, Set[str]]:
    """Parse bullets under each `### <Segment>` after `<!-- AUTO-INDEX -->`.

    Returns dict mapping segment name → set of IDs (extracted from `- `<id>` \\`—<title>`).
    Empty dict if AUTO-INDEX sentinel missing.
    """
    if _AUTO_INDEX_SENTINEL not in text:
        return {}
    after = text.split(_AUTO_INDEX_SENTINEL, 1)[1]
    segments: Dict[str, Set[str]] = {}
    current = None
    for line in after.splitlines():
        m = _SEGMENT_HEADER_RE.match(line.strip())
        if m:
            current = m.group(1)
            segments.setdefault(current, set())
            continue
        if current is None:
            continue
        bm = _BULLET_ID_RE.match(line.strip())
        if bm:
            segments[current].add(bm.group(1))
    return segments


def validate_adr_links(text: str, adr_docs_dir: Path) -> List[dict]:
    """Find ADR markdown links and verify target exists in adr_docs_dir.

    Returns list of {snippet, fix_hint} dicts (caller maps to Finding).
    Only validates ADR-NNNN links; ignores other markdown links.
    """
    findings: List[dict] = []
    if not adr_docs_dir.is_dir():
        return findings
    for m in _ADR_LINK_RE.finditer(text):
        adr_filename = m.group(2)
        target = adr_docs_dir / adr_filename
        if not target.is_file():
            findings.append({
                "snippet": f"ADR link target {adr_filename} not found in {adr_docs_dir}",
                "fix_hint": f"create {adr_filename} or fix the link target",
            })
    return findings


def validate_index_segment_sync(
    segments: Dict[str, Set[str]], roadmap_root: Path
) -> List[dict]:
    """Compare `### Phases` segment IDs to phases/*.md files on disk.

    Detects drift in either direction (segment missing on disk, or disk missing in segment).
    Only checks `Phases` segment by default; other segments can be checked by the
    caller's category-specific logic (roadmap-feature checks Features, etc.).

    Returns list of {snippet, fix_hint} dicts.
    """
    findings: List[dict] = []
    disk_phases: Set[str] = set()
    phases_dir = roadmap_root / "phases"
    if phases_dir.is_dir():
        for f in phases_dir.glob("phase-*.md"):
            stem = f.stem  # e.g. "phase-1"
            disk_phases.add(stem)
    seg_phases = segments.get("Phases", set())
    for pid in sorted(disk_phases - seg_phases):
        findings.append({
            "snippet": f"{pid}: disk phase file exists but missing from AUTO-INDEX Phases segment",
            "fix_hint": "rddf roadmap --reindex or manually add to AUTO-INDEX",
        })
    for pid in sorted(seg_phases - disk_phases):
        findings.append({
            "snippet": f"AUTO-INDEX Phases references '{pid}' but no phase file exists",
            "fix_hint": "remove stale entry or recreate phase file",
        })
    return findings