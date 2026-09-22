"""rdd-doctor category: roadmap-feature.

Per feat-roadmap-discovery-completion proposal AC-5.

Read-only diagnostic enforcing 3 invariants:
  1. Each .rddf/roadmap/features/*.md frontmatter has required fields
  2. iteration.json::feature_view.features includes all active feature ids
  3. AGENTS.md AUTO sentinel block (if present) matches fragment list

No file modification (READ-ONLY). Reuses _lib.roadmap_state.load_fragments.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from doctor_render import Finding, Severity  # noqa: E402
from _lib.roadmap_state import (  # noqa: E402
    AGENTS_AUTO_SENTINEL_END,
    AGENTS_AUTO_SENTINEL_START,
    load_fragments,
)


_REQUIRED_FIELDS = ("id", "kind", "status", "phase_refs", "主题")


def _frontmatter_field_keys(frontmatter_text: str) -> set[str]:
    """Return set of top-level YAML keys present in the frontmatter block.

    Lightweight parser — only enumerates top-level keys, ignores values.
    Sufficient for the "required field missing" check.
    """
    keys: set[str] = set()
    for raw_line in frontmatter_text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or ":" not in line:
            continue
        key, _, _ = line.partition(":")
        key = key.strip()
        if key:
            keys.add(key)
    return keys


def _check_frontmatter(tmp_path: Path) -> List[Finding]:
    fragments = load_fragments(str(tmp_path / ".rddf" / "roadmap"))
    features = [f for f in fragments if f.kind == "feature"]
    findings: List[Finding] = []
    for feat in features:
        # Re-derive raw frontmatter to enumerate top-level keys
        try:
            fm_text = Path(feat.file_path).read_text(encoding="utf-8").split(
                "---", 2
            )[1]
        except (OSError, UnicodeDecodeError, IndexError):
            continue
        present_keys = _frontmatter_field_keys(fm_text)
        for field in _REQUIRED_FIELDS:
            if field not in present_keys:
                findings.append(Finding(
                    severity=Severity.WARNING,
                    category="roadmap-feature.frontmatter",
                    file=feat.file_path,
                    line=None,
                    snippet=f"{feat.id}: missing required field '{field}'",
                    fix_hint=(
                        f"add '{field}: <value>' to {Path(feat.file_path).name} "
                        f"frontmatter"
                    ),
                ))
    return findings


def _check_iteration_view(tmp_path: Path) -> List[Finding]:
    state_path = tmp_path / ".rddf" / "state" / "iteration.json"
    if not state_path.is_file():
        return []
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    feature_view = data.get("feature_view", {})
    view_features = feature_view.get("features", {}) if isinstance(
        feature_view, dict
    ) else {}
    known_ids = set(view_features.keys())

    fragments = load_fragments(str(tmp_path / ".rddf" / "roadmap"))
    active_features = {
        f.id for f in fragments
        if f.kind == "feature" and f.status == "active"
    }
    missing = active_features - known_ids
    findings: List[Finding] = []
    for feat_id in sorted(missing):
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="roadmap-feature.iteration-drift",
            file=str(state_path),
            line=None,
            snippet=(
                f"iteration.json feature_view missing active feature '{feat_id}'"
            ),
            fix_hint=(
                "rddf feature (auto-recovery via planner stage exit); "
                "or run `rddf doctor --category roadmap-feature` after fix"
            ),
        ))
    return findings


def _check_agents_md_auto_block(tmp_path: Path) -> List[Finding]:
    agents_path = tmp_path / "AGENTS.md"
    if not agents_path.is_file():
        return []
    try:
        content = agents_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    if AGENTS_AUTO_SENTINEL_START not in content:
        return []
    if AGENTS_AUTO_SENTINEL_END not in content:
        return []

    start = content.index(AGENTS_AUTO_SENTINEL_START)
    end = content.index(AGENTS_AUTO_SENTINEL_END, start) + len(
        AGENTS_AUTO_SENTINEL_END
    )
    block = content[start:end]

    advertised: set[str] = set()
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line.startswith("| `feat-") and not line.startswith("| feat-"):
            continue
        m = re.match(r"^\|\s*`?(feat-[a-z0-9-]+)`?\s*\|", line)
        if m:
            advertised.add(m.group(1))

    fragments = load_fragments(str(tmp_path / ".rddf" / "roadmap"))
    known_ids = {
        f.id for f in fragments
        if f.kind == "feature" and f.status != "archived"
    }

    stale = advertised - known_ids
    findings: List[Finding] = []
    for feat_id in sorted(stale):
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="roadmap-feature.agents-drift",
            file=str(agents_path),
            line=None,
            snippet=(
                f"AGENTS.md AUTO block contains stale feature id '{feat_id}'"
            ),
            fix_hint="rddf roadmap --update-agent-md",
        ))
    return findings


def run(project_root: Path | None = None) -> List[Finding]:
    """Run all 3 roadmap-feature invariants; READ-ONLY.

    Returns list of Finding (empty = healthy). Exits via exit_code_for:
      0 = healthy, 1 = WARNING, 2 = CRITICAL, 3 = internal error.
    """
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings: List[Finding] = []
    findings.extend(_check_frontmatter(project_root))
    findings.extend(_check_iteration_view(project_root))
    findings.extend(_check_agents_md_auto_block(project_root))
    return findings