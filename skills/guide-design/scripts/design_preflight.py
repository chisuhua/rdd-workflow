"""Theme coverage computation for guide-design preflight display.

Scans roadmap.md for expected improvement themes, cross-references with
`.rddf/improvements/*.md` proposals that declare `**主题**:` fields, and
returns a coverage summary dict.

Excludes `~skipped~` themes from the denominator. Counts legacy proposals
without `**主题**:` separately (no false 0/N alarm for old projects).
"""
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


_SUBJECT_RE = re.compile(r"^\*\*主题\*\*\s*:\s*(.+?)\s*$", re.MULTILINE)
_SKIPPED_SUFFIX = "~skipped~"
_PHASE_HEADER_RE = re.compile(r"### Phase \d+:[^\n]*?\(phase-[a-z0-9-]+\)")
_CATEGORY_TABLE_HEADER_RE = re.compile(r"\|\s*分类ID\s*\|\s*名称\s*\|\s*描述\s*\|\s*优先级\s*\|\s*预期改进方向\s*\|")


def _parse_themes_cell(cell: str) -> List[str]:
    """Split a 5th-column cell by ;/； and return clean theme names."""
    if not cell.strip():
        return []
    parts = re.split(r"[；;]", cell)
    return [p.strip() for p in parts if p.strip()]


def _read_roadmap_themes(roadmap_path: str) -> List[Dict[str, str]]:
    """Parse roadmap.md, return list of {phase, category, theme} dicts."""
    content = Path(roadmap_path).read_text(encoding="utf-8")
    themes = []

    for phase_match in _PHASE_HEADER_RE.finditer(content):
        pid_match = re.search(r"\((phase-[a-z0-9-]+)\)", phase_match.group(0))
        if not pid_match:
            continue
        phase_id = pid_match.group(1)

        start = phase_match.end()
        next_phase = _PHASE_HEADER_RE.search(content, start)
        end = start + next_phase.start() if next_phase else len(content)
        phase_section = content[start:end]

        for line in phase_section.splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 5:
                continue
            if cells[0] in {"分类ID", "--------"} or set(cells[0]) <= {"-"}:
                continue
            for theme in _parse_themes_cell(cells[4]):
                themes.append({
                    "phase": phase_id,
                    "category": cells[0],
                    "theme": theme,
                })

    return themes


def _read_proposal_subjects(improvements_dir: str) -> tuple[List[str], int]:
    """Scan improvements/*.md for **主题** fields.

    Returns (matched_subjects, unmapped_legacy_count).
    """
    matched: List[str] = []
    unmapped_legacy = 0
    p = Path(improvements_dir)
    if not p.is_dir():
        return matched, unmapped_legacy

    for f in p.glob("*.md"):
        content = f.read_text(encoding="utf-8")
        m = _SUBJECT_RE.search(content)
        if m:
            subject = m.group(1).strip()
            if subject and subject != "不适用":
                matched.append(subject)
        else:
            unmapped_legacy += 1

    return matched, unmapped_legacy


def compute_theme_coverage(
    project_root: str,
    roadmap_path: str,
    improvements_dir: str,
) -> Dict[str, Any]:
    """Compute theme coverage: matched / total / uncovered / legacy.

    Returns dict with:
      - total_themes: int (excluding ~skipped~)
      - covered: int (proposals whose 主题 matches a theme)
      - uncovered: list[str] (theme names not matched)
      - coverage_pct: float
      - unmapped_legacy_count: int (proposals without 主题 field)
      - skipped_count: int (~skipped~ themes excluded from denominator)
    """
    themes = _read_roadmap_themes(roadmap_path)
    subjects, legacy_count = _read_proposal_subjects(improvements_dir)

    active_names = []
    skipped_count = 0
    for t in themes:
        name = t["theme"].strip()
        if name.endswith(_SKIPPED_SUFFIX):
            skipped_count += 1
            continue
        active_names.append(name)

    covered = [name for name in active_names if name in subjects]
    uncovered = [name for name in active_names if name not in subjects]

    total = len(active_names)
    coverage_pct = round(100 * len(covered) / total, 1) if total > 0 else 100.0

    return {
        "total_themes": total,
        "covered": len(covered),
        "uncovered": uncovered,
        "coverage_pct": coverage_pct,
        "unmapped_legacy_count": legacy_count,
        "skipped_count": skipped_count,
    }


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: design_preflight.py <project_root> <roadmap_path> <improvements_dir>",
            file=sys.stderr,
        )
        return 1
    result = compute_theme_coverage(sys.argv[1], sys.argv[2], sys.argv[3])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())