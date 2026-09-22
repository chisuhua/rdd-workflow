"""rdd-doctor category: roadmap-feature.

Per feat-roadmap-discovery-completion proposal AC-5.

Read-only diagnostic enforcing 6 invariants:
  1. Each .rddf/roadmap/features/*.md frontmatter has required fields
  2. Fragments with status=done/archived appear in .rddf/roadmap.md AUTO-INDEX
  3. iteration.json::feature_view.features includes all active feature ids
     AND status matches fragment files
  4. AGENTS.md AUTO sentinel block (if present) matches fragment list
  5. AGENTS.md AUTO sentinel block is present (not silently missing)
  6. AGENTS.md AUTO block status column matches fragment status

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
                # Missing 'status' is CRITICAL; other fields WARNING
                sev = Severity.CRITICAL if field == "status" else Severity.WARNING
                findings.append(Finding(
                    severity=sev,
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


def _check_roadmap_md_index(tmp_path: Path) -> List[Finding]:
    """Check fragment presence in .rddf/roadmap.md AUTO-INDEX Features section.

    CRITICAL: fragment status='done'/'archived' but not in AUTO-INDEX Features.
    CRITICAL: fragment status='active'/'proposed'/'ready' but not in AUTO-INDEX Features.
    """
    roadmap_path = tmp_path / ".rddf" / "roadmap.md"
    if not roadmap_path.is_file():
        return []

    try:
        content = roadmap_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    if "<!-- AUTO-INDEX -->" not in content:
        return []

    # Parse Features section under AUTO-INDEX
    after_auto = content.split("<!-- AUTO-INDEX -->", 1)[1]
    features_match = re.search(
        r"### Features\n(.*?)(?=\n### |\n## |\Z)", after_auto, re.DOTALL
    )
    indexed_features: set[str] = set()
    if features_match:
        for line in features_match.group(1).splitlines():
            m = re.match(r"-\s*`(feat-[a-z0-9-]+)`\s*—", line)
            if m:
                indexed_features.add(m.group(1))

    fragments = load_fragments(str(tmp_path / ".rddf" / "roadmap"))
    features = [f for f in fragments if f.kind == "feature"]

    findings: List[Finding] = []
    for feat in features:
        if feat.id not in indexed_features:
            sev = (
                Severity.CRITICAL
                if feat.status in ("done", "archived")
                else Severity.WARNING
            )
            findings.append(Finding(
                severity=sev,
                category="roadmap-feature.roadmap-index-drift",
                file=str(roadmap_path),
                line=None,
                snippet=(
                    f"{feat.id}: status={feat.status} missing from "
                    f"AUTO-INDEX Features section"
                ),
                fix_hint="rddf roadmap add-feature (re-fragment-index)",
            ))

    # Also check for stale entries in AUTO-INDEX (indexed but no fragment)
    known_ids = {f.id for f in features}
    stale_in_index = indexed_features - known_ids
    for feat_id in sorted(stale_in_index):
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="roadmap-feature.roadmap-index-drift",
            file=str(roadmap_path),
            line=None,
            snippet=(
                f"AUTO-INDEX Features section references '{feat_id}' "
                f"but no matching fragment file exists"
            ),
            fix_hint="rddf roadmap --reindex or manually remove stale entry",
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
    features = [f for f in fragments if f.kind == "feature"]

    findings: List[Finding] = []

    # Check 1: active features missing from iteration.json
    active_features = {f.id for f in features if f.status == "active"}
    missing = active_features - known_ids
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

    # Check 2: status alignment — fragment says 'done' but iteration.json disagrees
    for feat in features:
        if feat.id not in known_ids:
            continue
        iter_status = view_features[feat.id].get("status", "")
        if feat.status == "done" and iter_status != "done":
            findings.append(Finding(
                severity=Severity.WARNING,
                category="roadmap-feature.iteration-drift",
                file=str(state_path),
                line=None,
                snippet=(
                    f"{feat.id}: fragment status=done but "
                    f"iteration.json shows status={iter_status}"
                ),
                fix_hint=(
                    "sync iteration.json via rddf feature or planner stage exit"
                ),
            ))
        elif feat.status == "active" and iter_status not in ("active", "ready", "proposed"):
            findings.append(Finding(
                severity=Severity.WARNING,
                category="roadmap-feature.iteration-drift",
                file=str(state_path),
                line=None,
                snippet=(
                    f"{feat.id}: fragment status=active but "
                    f"iteration.json shows status={iter_status}"
                ),
                fix_hint="sync iteration.json via rddf feature",
            ))

    # Check 3: stale entries in iteration.json (no longer a feature fragment)
    fragment_ids = {f.id for f in features}
    stale_in_iter = known_ids - fragment_ids
    for feat_id in sorted(stale_in_iter):
        if feat_id == "__ungrouped__":
            continue  # special internal key
        findings.append(Finding(
            severity=Severity.WARNING,
            category="roadmap-feature.iteration-drift",
            file=str(state_path),
            line=None,
            snippet=(
                f"iteration.json has '{feat_id}' but no matching fragment file"
            ),
            fix_hint="re-run rddf feature or cleanup iteration.json",
        ))

    return findings


def _check_agents_md_auto_block(tmp_path: Path) -> List[Finding]:
    agents_path = tmp_path / "AGENTS.md"
    findings: List[Finding] = []

    # Check 1: Does AGENTS.md exist?
    if not agents_path.is_file():
        fragments = load_fragments(str(tmp_path / ".rddf" / "roadmap"))
        features = [f for f in fragments if f.kind == "feature"]
        if features:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="roadmap-feature.agents-drift",
                file="AGENTS.md",
                line=None,
                snippet="AGENTS.md not found; cannot verify AUTO sentinel block",
                fix_hint="create AGENTS.md with `rddf roadmap --update-agent-md`",
            ))
        return findings

    try:
        content = agents_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return findings

    # Check 2: Sentinel block missing
    has_start = AGENTS_AUTO_SENTINEL_START in content
    has_end = AGENTS_AUTO_SENTINEL_END in content
    if not has_start or not has_end:
        fragments = load_fragments(str(tmp_path / ".rddf" / "roadmap"))
        features = [f for f in fragments if f.kind == "feature"]
        if features:
            missing_sentinels = "start" if not has_start else "end"
            findings.append(Finding(
                severity=Severity.WARNING,
                category="roadmap-feature.agents-drift",
                file="AGENTS.md",
                line=None,
                snippet=(
                    f"AGENTS.md missing AUTO sentinel block "
                    f"(<!-- {missing_sentinels} --> not found)"
                ),
                fix_hint="rddf roadmap --update-agent-md",
            ))
        return findings

    # Check 3: Empty sentinel block (no features while fragments exist)
    start = content.index(AGENTS_AUTO_SENTINEL_START)
    end = content.index(AGENTS_AUTO_SENTINEL_END, start) + len(
        AGENTS_AUTO_SENTINEL_END
    )
    block = content[start:end]

    advertised_ids: set[str] = set()
    advertised_status: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line.startswith("| `feat-") and not line.startswith("| feat-"):
            continue
        m = re.match(r"^\|\s*`?(feat-[a-z0-9-]+)`?\s*\|\s*(\S+)", line)
        if m:
            fid = m.group(1)
            st = m.group(2)
            advertised_ids.add(fid)
            advertised_status[fid] = st

    fragments = load_fragments(str(tmp_path / ".rddf" / "roadmap"))
    features = [f for f in fragments if f.kind == "feature"]

    # Check 4: stale entries in AGENTS.md (advertised but no fragment on disk)
    known_ids = {f.id for f in features}
    stale = advertised_ids - known_ids
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

    # Check 5: fragments on disk but not in AGENTS.md
    missing_in_agents = known_ids - advertised_ids
    for feat_id in sorted(missing_in_agents):
        findings.append(Finding(
            severity=Severity.CRITICAL,
            category="roadmap-feature.agents-drift",
            file=str(agents_path),
            line=None,
            snippet=(
                f"fragment '{feat_id}' exists on disk but not in "
                f"AGENTS.md AUTO block"
            ),
            fix_hint="rddf roadmap --update-agent-md",
        ))

    # Check 6: status mismatch between fragment and AGENTS.md table
    feat_map = {f.id: f for f in features}
    common_ids = known_ids & advertised_ids
    for feat_id in sorted(common_ids):
        fragment_status = feat_map[feat_id].status
        agents_status = advertised_status.get(feat_id, "")
        if agents_status and fragment_status != agents_status:
            findings.append(Finding(
                severity=Severity.WARNING,
                category="roadmap-feature.agents-drift",
                file=str(agents_path),
                line=None,
                snippet=(
                    f"{feat_id}: fragment status={fragment_status} but "
                    f"AGENTS.md shows status={agents_status}"
                ),
                fix_hint="rddf roadmap --update-agent-md",
            ))

    return findings


def run(project_root: Path | None = None) -> List[Finding]:
    """Run all roadmap-feature invariants; READ-ONLY.

    Returns list of Finding (empty = healthy). Exits via exit_code_for:
      0 = healthy, 1 = WARNING, 2 = CRITICAL, 3 = internal error.
    """
    if project_root is None:
        project_root = Path(os.environ.get("RDDF_PROJECT_ROOT", "."))
    findings: List[Finding] = []
    findings.extend(_check_frontmatter(project_root))
    findings.extend(_check_roadmap_md_index(project_root))
    findings.extend(_check_iteration_view(project_root))
    findings.extend(_check_agents_md_auto_block(project_root))
    return findings