"""list_active_features — enumerate roadmap features with name + description.

Per improve-roadmap-feature-discovery proposal: AI agents starting a session
need to discover which feature fragments exist under .rddf/roadmap/features/
so the `feat-fix-audit-findings` style features can be referenced from
AGENTS.md without being silently lost.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Dict


_NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
_DESC_RE = re.compile(r"^description:\s*(.+?)\s*$", re.MULTILINE)
_REF_RE = re.compile(r"^[-*]?\s*phase-refs:\s*\[([^\]]+)\]", re.MULTILINE)


def list_active_features(project_root: Path) -> List[Dict[str, object]]:
    """Return list of {name, description, phase_refs} for each .rddf/roadmap/features/*.md.

    Empty list when the features dir does not exist or no feature files
    carry a top-level frontmatter name field.
    """
    features_dir = Path(project_root) / ".rddf" / "roadmap" / "features"
    if not features_dir.is_dir():
        return []

    out: List[Dict[str, object]] = []
    for entry in sorted(features_dir.glob("*.md")):
        if not entry.is_file():
            continue
        text = entry.read_text(encoding="utf-8")

        m_name = _NAME_RE.search(text)
        if not m_name:
            continue
        name = m_name.group(1).strip().strip('"').strip("'")

        m_desc = _DESC_RE.search(text)
        description = m_desc.group(1).strip() if m_desc else ""

        refs: List[str] = []
        m_ref = _REF_RE.search(text)
        if m_ref:
            refs = [r.strip().strip('"').strip("'") for r in m_ref.group(1).split(",")]

        out.append({
            "name": name,
            "description": description,
            "phase_refs": refs,
            "path": str(entry),
        })
    return out


if __name__ == "__main__":
    import json, sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    features = list_active_features(root)
    print(json.dumps(features, ensure_ascii=False, indent=2))