# Add roadmap-phases + roadmap-md-integrity Categories Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 2 read-only diagnostic categories to `rdd-doctor`: `roadmap-phases` (validates `.rddf/roadmap/phases/*.md`) and `roadmap-md-integrity` (validates `.rddf/roadmap.md` table schema, AUTO-INDEX segments, ADR links, AUTO-SPRINT sync). Bring the doctor category count from 18 → 20.

**Architecture:** Each new category lives in its own check file under `skills/rdd-doctor/scripts/checks/`. The markdown-table parsing helper functions live in a new `_lib/roadmap_md_integrity.py` module. The phase sync check reuses `_lib/roadmap_state.load_fragments` (existing helper). Severity policy mirrors `roadmap-feature` (missing `status` = CRITICAL; drift = CRITICAL; advisory = WARNING).

**Tech Stack:** Python 3.12, stdlib only (`pathlib`, `re`, `json`, `dataclass`). pytest unit + bats integration. No new dependencies.

**Reference Spec:** `.rddf/improvements/add-roadmap-phases-and-md-integrity-category.md`

**Reference Pattern Files (verified working — copy structure):**
- `skills/rdd-doctor/scripts/checks/roadmap_refs_check.py` (5-level `_PROJECT_ROOT` pattern, thin wrapper)
- `skills/rdd-doctor/scripts/checks/roadmap_feature_check.py:_check_frontmatter` (frontmatter iteration pattern)

---

## File Map

| File | Action | Reason |
|---|---|---|
| `tests/unit/test_roadmap_phases.py` | CREATE | 4 unit cases for new `roadmap_phases_check.run` |
| `tests/unit/test_roadmap_md_integrity.py` | CREATE | 6 unit cases for `_lib.roadmap_md_integrity` pure helpers |
| `_lib/roadmap_md_integrity.py` | CREATE | Public helpers: `parse_main_doc_table`, `parse_auto_index_segments`, `validate_adr_links`, `validate_index_segment_sync` |
| `skills/rdd-doctor/scripts/checks/roadmap_phases_check.py` | CREATE | Check module — runs 4 invariants on phases/ |
| `skills/rdd-doctor/scripts/checks/roadmap_md_integrity_check.py` | CREATE | Check module — runs 5 invariants on .rddf/roadmap.md |
| `skills/rdd-doctor/scripts/doctor_main.py` | EDIT | Add 2 imports + 2 `_CHECKERS` dict entries |
| `skills/rdd-doctor/SKILL.md` | EDIT | Table header `18` → `20`, append 2 table rows, extend `--category` list, append 2 lines to quick-reference section |

---

## Task 1: Write `roadmap-phases` check (TDD)

**Files:**
- Create: `tests/unit/test_roadmap_phases.py`
- Create: `skills/rdd-doctor/scripts/checks/roadmap_phases_check.py`

- [ ] **Step 1.1: Write the failing test (4 cases)**

Create `tests/unit/test_roadmap_phases.py`:

```python
"""Unit tests for skills/rdd-doctor/scripts/checks/roadmap_phases_check.py."""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "rdd-doctor" / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from doctor_render import Severity  # noqa: E402
from checks.roadmap_phases_check import run  # noqa: E402


def _setup_repo(tmp_path: Path, *, phase_files: dict[str, str], main_doc: str) -> Path:
    """Create a minimal repo with phases/*.md + .rddf/roadmap.md under tmp_path."""
    repo = tmp_path
    phases_dir = repo / ".rddf" / "roadmap" / "phases"
    phases_dir.mkdir(parents=True, exist_ok=True)
    for name, body in phase_files.items():
        (phases_dir / name).write_text(body, encoding="utf-8")
    (repo / ".rddf").mkdir(exist_ok=True)
    (repo / ".rddf" / "roadmap.md").write_text(main_doc, encoding="utf-8")
    return repo


def test_roadmap_phases_happy(tmp_path: Path):
    """All phases present, frontmatter complete, AUTO-INDEX matches."""
    main_doc = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 提案生成 | active | | |
| phase-2 | 阶段步骤化 | active | | |

<!-- AUTO-INDEX -->

### Phases
- `phase-1` — 提案生成
- `phase-2` — 阶段步骤化
"""
    repo = _setup_repo(tmp_path, phase_files={
        "phase-1.md": "---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n主题: 提案生成\n---\nbody\n",
        "phase-2.md": "---\nid: phase-2\nkind: phase\nstatus: active\nphase_refs: []\n主题: 阶段步骤化\n---\nbody\n",
    }, main_doc=main_doc)
    findings = run(project_root=repo)
    assert findings == [], f"expected clean, got: {findings}"


def test_roadmap_phases_missing_frontmatter_field(tmp_path: Path):
    """Phase file missing 'status' field → CRITICAL."""
    main_doc = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 提案生成 | active | | |

<!-- AUTO-INDEX -->

### Phases
- `phase-1` — 提案生成
"""
    repo = _setup_repo(tmp_path, phase_files={
        "phase-1.md": "---\nid: phase-1\nkind: phase\nphase_refs: []\n主题: 提案生成\n---\nbody\n",
    }, main_doc=main_doc)
    findings = run(project_root=repo)
    assert any(f.severity == Severity.CRITICAL and "status" in f.snippet for f in findings), \
        f"expected CRITICAL missing-status, got: {findings}"


def test_roadmap_phases_auto_index_drift(tmp_path: Path):
    """Phase file on disk but missing from AUTO-INDEX → CRITICAL."""
    main_doc = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | T | active | | |

<!-- AUTO-INDEX -->

### Phases
"""
    repo = _setup_repo(tmp_path, phase_files={
        "phase-1.md": "---\nid: phase-1\nkind: phase\nstatus: active\nphase_refs: []\n主题: T\n---\nbody\n",
    }, main_doc=main_doc)
    findings = run(project_root=repo)
    assert any(f.severity == Severity.CRITICAL and "phase-1" in f.snippet for f in findings), \
        f"expected CRITICAL AUTO-INDEX drift, got: {findings}"


def test_roadmap_phases_main_doc_missing(tmp_path: Path):
    """Phase referenced in main doc but no phase file → CRITICAL."""
    main_doc = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-99 | T | active | | |

<!-- AUTO-INDEX -->

### Phases
- `phase-99` — phantom
"""
    repo = _setup_repo(tmp_path, phase_files={}, main_doc=main_doc)
    findings = run(project_root=repo)
    assert any(f.severity == Severity.CRITICAL and "phase-99" in f.snippet for f in findings), \
        f"expected CRITICAL main-doc missing phase-99, got: {findings}"
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `pytest tests/unit/test_roadmap_phases.py -v`
Expected: collection FAIL with `ModuleNotFoundError: No module named 'checks.roadmap_phases_check'`

- [ ] **Step 1.3: Implement the check module**

Create `skills/rdd-doctor/scripts/checks/roadmap_phases_check.py`:

```python
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
```

- [ ] **Step 1.4: Run tests to verify they pass**

Run: `pytest tests/unit/test_roadmap_phases.py -v`
Expected: 4/4 PASS

- [ ] **Step 1.5: Commit**

```bash
git add tests/unit/test_roadmap_phases.py skills/rdd-doctor/scripts/checks/roadmap_phases_check.py
git commit -m "feat(rdd-doctor): add roadmap-phases category for .rddf/roadmap/phases/*.md validation"
```

---

## Task 2: Write `roadmap-md-integrity` check + `_lib/roadmap_md_integrity.py` (TDD)

**Files:**
- Create: `tests/unit/test_roadmap_md_integrity.py`
- Create: `_lib/roadmap_md_integrity.py`
- Create: `skills/rdd-doctor/scripts/checks/roadmap_md_integrity_check.py`

- [ ] **Step 2.1: Write the failing test (6 cases for `_lib/roadmap_md_integrity` pure helpers)**

Create `tests/unit/test_roadmap_md_integrity.py`:

```python
"""Unit tests for _lib/roadmap_md_integrity.py — pure parsing helpers."""
from __future__ import annotations

from pathlib import Path

import pytest

from _lib.roadmap_md_integrity import (
    parse_main_doc_table,
    parse_auto_index_segments,
    validate_adr_links,
    validate_index_segment_sync,
)


GOOD_MAIN = """# Roadmap

## Phase Skeleton
| Phase | Theme | Status | Started | Done |
|-------|-------|--------|---------|------|
| phase-1 | 完整多会话支持 | active | | |
| phase-1 | 定时循环 | active | | |
| phase-2 | 编排能力 | active | | |

<!-- AUTO-INDEX -->

### Phases
- `phase-1` — 完整多会话支持
- `phase-2` — 编排能力

### Features
- `feat-a` — A (refs: phase-1)

### Objectives
- `objective-y` — O

<!-- AUTO-SPRINT-START -->
## Current Sprint
| Project | Phase |
|---------|-------|
| rdd-workflow | phase-1 |
"""


def test_parse_main_doc_table_happy():
    rows = parse_main_doc_table(Path("/tmp/x.md"), GOOD_MAIN)
    assert rows == [
        ("phase-1", "完整多会话支持", "active", "", ""),
        ("phase-1", "定时循环", "active", "", ""),
        ("phase-2", "编排能力", "active", "", ""),
    ]


def test_parse_main_doc_table_bad_columns(tmp_path: Path):
    body = """## Phase Skeleton
| Phase | Theme | Done |
|-------|-------|------|
| phase-1 | T | |
"""
    rows = parse_main_doc_table(tmp_path / "x.md", body)
    assert rows == []  # wrong column count → no parse


def test_parse_auto_index_segments_happy():
    segs = parse_auto_index_segments(GOOD_MAIN)
    assert "Phases" in segs and "Features" in segs and "Objectives" in segs
    assert "phase-1" in segs["Phases"]
    assert "feat-a" in segs["Features"]


def test_parse_auto_index_segments_missing_objectives():
    body = """<!-- AUTO-INDEX -->

### Phases
- `phase-1` — T
"""
    segs = parse_auto_index_segments(body)
    assert "Phases" in segs
    assert "Objectives" not in segs  # missing segment


def test_validate_adr_links_valid(tmp_path: Path):
    adr = tmp_path / "ADR-0010-foo.md"
    adr.write_text("x", encoding="utf-8")
    body = "| T | [ADR-0010](../foo/{}) | |".format(adr.name)
    findings = validate_adr_links(body, adr_docs_dir=tmp_path)
    assert findings == []


def test_validate_adr_links_broken(tmp_path: Path):
    body = "| T | [ADR-9999](../foo/ADR-9999-ghost.md) | |"
    findings = validate_adr_links(body, adr_docs_dir=tmp_path)
    assert any("ADR-9999" in f["snippet"] for f in findings)


def test_validate_index_segment_sync_happy(tmp_path: Path):
    """Phases segment + phases dir agree."""
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-1.md").write_text("x", encoding="utf-8")
    segs = {"Phases": {"phase-1"}, "Features": set(), "Objectives": set()}
    findings = validate_index_segment_sync(segs, tmp_path / ".rddf" / "roadmap")
    assert findings == []


def test_validate_index_segment_sync_drift(tmp_path: Path):
    (tmp_path / ".rddf" / "roadmap" / "phases").mkdir(parents=True)
    segs = {"Phases": set(), "Features": set(), "Objectives": set()}
    findings = validate_index_segment_sync(segs, tmp_path / ".rddf" / "roadmap")
    assert any("phase-1" in f["snippet"] for f in findings) is False  # no phase-1 on disk → no drift
    # Add phantom on disk:
    (tmp_path / ".rddf" / "roadmap" / "phases" / "phase-2.md").write_text("x", encoding="utf-8")
    findings = validate_index_segment_sync(segs, tmp_path / ".rddf" / "roadmap")
    assert any("phase-2" in f["snippet"] for f in findings)
```

- [ ] **Step 2.2: Run tests to verify they fail**

Run: `pytest tests/unit/test_roadmap_md_integrity.py -v`
Expected: collection FAIL with `ModuleNotFoundError: No module named '_lib.roadmap_md_integrity'`

- [ ] **Step 2.3: Implement `_lib/roadmap_md_integrity.py`**

Create `_lib/roadmap_md_integrity.py`:

```python
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
            rows.append(m.groups())
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
```

- [ ] **Step 2.4: Run tests to verify they pass**

Run: `pytest tests/unit/test_roadmap_md_integrity.py -v`
Expected: 8/8 PASS (test_parse_main_doc_table_happy, test_parse_main_doc_table_bad_columns, test_parse_auto_index_segments_happy, test_parse_auto_index_segments_missing_objectives, test_validate_adr_links_valid, test_validate_adr_links_broken, test_validate_index_segment_sync_happy, test_validate_index_segment_sync_drift)

- [ ] **Step 2.5: Implement `roadmap_md_integrity_check.py` check module**

Create `skills/rdd-doctor/scripts/checks/roadmap_md_integrity_check.py`:

```python
"""rdd-doctor category: roadmap-md-integrity (per add-roadmap-phases-and-md-integrity-category).

Read-only diagnostic that validates `.rddf/roadmap.md` markdown structure:
  B1. Phase Skeleton table has 5 columns (Phase / Theme / Status / Started / Done)
  B2. AUTO-INDEX has all 3 sub-segments (Phases / Features / Objectives)
  B3. Phases segment ↔ .rddf/roadmap/phases/*.md disk sync
  B4. ADR links in table cells resolve to existing docs/adr/*.md
  B5. (Advisory) AUTO-SPRINT-START Current Sprint phase column ⊆ Phases segment

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
from _lib.roadmap_state import load_fragments


_AUTO_SPRINT_SENTINEL = "<!-- AUTO-SPRINT-START -->"


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
        if status and status not in ("active", "deferred", "completed", "archived"):
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
```

- [ ] **Step 2.6: Re-run tests to verify everything still passes**

Run: `pytest tests/unit/test_roadmap_md_integrity.py tests/unit/test_roadmap_phases.py -v`
Expected: 12/12 PASS (8 + 4)

- [ ] **Step 2.7: Commit**

```bash
git add tests/unit/test_roadmap_md_integrity.py _lib/roadmap_md_integrity.py skills/rdd-doctor/scripts/checks/roadmap_md_integrity_check.py
git commit -m "feat(rdd-doctor): add roadmap-md-integrity category for .rddf/roadmap.md table validation"
```

---

## Task 3: Wire into doctor_main + sync SKILL.md

**Files:**
- Modify: `skills/rdd-doctor/scripts/doctor_main.py` (add 2 imports + 2 `_CHECKERS` entries)
- Modify: `skills/rdd-doctor/SKILL.md` (header 18→20, 2 table rows, --category list, 2 quick-ref lines)

- [ ] **Step 3.1: Update `doctor_main.py` to register new categories**

In `skills/rdd-doctor/scripts/doctor_main.py`, replace the imports block:

```python
from checks import (
    ai_context_bootstrap_check,
    arch_audit_check,
    bypass_audit_check,
    docs_consistency_check,
    gitignore_check,
    improvement_frontmatter_check,
    migration_residue_check,
    objective_lifecycle_check,
    objective_structure_check,
    orphan_gates_check,
    plan_tdd_check,
    proposal_section_check,
    proposal_table_check,
    roadmap_feature_check,
    roadmap_md_integrity_check,
    roadmap_meta_check,
    roadmap_phases_check,
    roadmap_refs_check,
    state_schema_check,
    tasks_checkbox_check,
)
```

and replace `_CHECKERS` dict entry block (the lines starting with `"roadmap-feature": roadmap_feature_check.run,` — add 2 new entries right after):

```python
    "roadmap-feature": roadmap_feature_check.run,
    "roadmap-md-integrity": roadmap_md_integrity_check.run,
    "roadmap-phases": roadmap_phases_check.run,
    "docs-consistency": docs_consistency_check.run,
```

- [ ] **Step 3.2: Run a smoke check that doctor.sh now lists 20 categories**

Run: `bash skills/rdd-doctor/scripts/doctor.sh --help 2>&1 | grep -oE '\{[^{}]+\}' | tr ',' '\n' | grep -E 'roadmap-'`
Expected: outputs include `roadmap-md-integrity`, `roadmap-phases`, `roadmap-refs`, `roadmap-feature`, `roadmap-meta`

- [ ] **Step 3.3: Verify SKILL.md sync test still passes (auto-locks 20 categories)**

Run: `bats tests/integration/test_rdd_doctor_skills_md_sync.bats`
Expected: 6/6 PASS (the test dynamically parses `_CHECKERS`, so it auto-detects 20)

- [ ] **Step 3.4: Update `SKILL.md` — extend --category list, change header, append 2 table rows, append 2 quick-ref lines**

In `skills/rdd-doctor/SKILL.md`, apply 4 edits:

**Edit 1** — line ~26, replace the `--category` list to include the new ones:

```bash
bash skills/rdd-doctor/scripts/doctor.sh [--json] [--category {state,plan-tdd,roadmap-meta,proposal-table,proposal-section,tasks-checkbox,migration-residue,orphan-gates,roadmap-refs,roadmap-feature,roadmap-md-integrity,roadmap-phases,docs-consistency,ai-context-bootstrap,gitignore,bypass-audit,improvement-frontmatter-consistency,objective-lifecycle,objective-structure,arch-audit}] [--quiet] [--help] [--version]
```

**Edit 2** — line ~40, update the `## 18 类检查概览` heading to `## 20 类检查概览` (line 40 contains the heading text in the table overview section; locate and replace `## 18 类检查概览` with `## 20 类检查概览`).

**Edit 3** — in the table (after the `roadmap-feature` row), insert 2 new rows:

```markdown
| `roadmap-phases` | `.rddf/roadmap/phases/*.md` frontmatter 必需字段 + AUTO-INDEX Phases 段同步 + main doc 一致性 | ✅ |
| `roadmap-md-integrity` | `.rddf/roadmap.md` `## Phase Skeleton` 表 schema + AUTO-INDEX 三段齐全 + ADR 链接有效 + AUTO-SPRINT drift | ✅ |
```

**Edit 4** — in the `.rddf/roadmap/` 文档诊断速查 section, append 2 lines after the existing 4 `bash` lines:

```bash
bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-phases        # .rddf/roadmap/phases/*.md 完整性 + main doc 引用一致
bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-md-integrity  # .rddf/roadmap.md 表 schema + AUTO-INDEX sync + ADR 链接
```

- [ ] **Step 3.5: Run SKILL.md sync test + SKILL.md sanity checks**

Run: `bats tests/integration/test_rdd_doctor_skills_md_sync.bats`
Expected: 6/6 PASS (table now has 20 rows; no SKILL.md ↔ _CHECKERS drift)

- [ ] **Step 3.6: Commit**

```bash
git add skills/rdd-doctor/scripts/doctor_main.py skills/rdd-doctor/SKILL.md
git commit -m "feat(rdd-doctor): wire roadmap-phases + roadmap-md-integrity into main dispatcher (18→20 categories)"
```

---

## Task 4: Full regression sweep + update KNOWN_FAILURES if needed

**Files:**
- Verify: `./test.sh --quick` exit 0 (bats recursive + pytest unit)
- Optionally: `./test.sh --full --regression` for full baseline check (per `add-full-regression-gate`)

- [ ] **Step 4.1: Run quick smoke**

Run: `./test.sh --quick`
Expected: 3127+ pytest PASS (incl. 10 new tests), bats smoke + static PASS, 0 new failures vs baseline

- [ ] **Step 4.2: Run new-category sanity check against master state**

Run:
```bash
bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-phases
bash skills/rdd-doctor/scripts/doctor.sh --category roadmap-md-integrity
```
Expected: exit 0 (master state is healthy post-merge)

- [ ] **Step 4.3: Run full regression gate (per `add-full-regression-gate` P0) — pre-archive mandatory**

Run: `./test.sh --full --regression`
Expected: exit 0; only KNOWN_FAILURES baseline entries fail (per `tests/scripts/report_regression.sh` baseline diff). New failures = 0.

- [ ] **Step 4.4: If new failures appear in regression: fix them OR add to KNOWN_FAILURES baseline**

If `tests/scripts/report_regression.sh` reports new failures (标记 "新增失败" 而非 "已知失败"):
- Option A: fix the underlying issue, re-run, commit fix
- Option B: if the failure is genuinely acceptable for now (e.g. flaky test), run `bash tests/scripts/refresh_known_failures.sh`, review diff, commit

- [ ] **Step 4.5: Commit (only if Step 4.4 made changes)**

```bash
git add tests/KNOWN_FAILURES.txt  # if updated
git commit -m "chore(tests): refresh KNOWN_FAILURES baseline after adding 2 rdd-doctor categories"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ A1 frontmatter → Task 1 Step 1.3 `_check_frontmatter`
- ✅ A2 AUTO-INDEX sync → Task 1 Step 1.3 `_check_auto_index`
- ✅ A3 main doc consistency → Task 1 Step 1.3 `_check_main_doc_consistency`
- ✅ A4 phase_refs self-ref → Task 1 Step 1.3 `_check_phase_refs_self_ref`
- ✅ B1 table schema → Task 2 Step 2.5 `_check_table_schema`
- ✅ B2 AUTO-INDEX segments → Task 2 Step 2.5 `_check_auto_index_segments`
- ✅ B3 segment ↔ disk sync → Task 2 Step 2.5 `_check_index_drift`
- ✅ B4 ADR links → Task 2 Step 2.5 `_check_adr_links`
- ✅ B5 AUTO-SPRINT drift → Task 2 Step 2.5 `_check_auto_sprint` (advisory)
- ✅ `_lib/roadmap_md_integrity.py` pure helpers → Task 2 Step 2.3
- ✅ `_CHECKERS` dict registration → Task 3 Step 3.1
- ✅ SKILL.md 18→20 sync → Task 3 Step 3.4
- ✅ `./test.sh --quick` regression → Task 4

**2. Placeholder scan:** No TBD/TODO/"implement later"/"add appropriate error handling" patterns. Every code step has full code blocks.

**3. Type consistency:**
- `_lib.roadmap_md_integrity.parse_main_doc_table(path, text) -> List[Tuple[str, str, str, str, str]]` (defined Step 2.3, used Step 2.5)
- `_lib.roadmap_md_integrity.parse_auto_index_segments(text) -> Dict[str, Set[str]]` (defined Step 2.3, used Step 2.5)
- `_lib.roadmap_md_integrity.validate_adr_links(text, adr_docs_dir) -> List[dict]` (defined Step 2.3, used Step 2.5)
- `_lib.roadmap_md_integrity.validate_index_segment_sync(segs, roadmap_root) -> List[dict]` (defined Step 2.3, used Step 2.5)
- `from _lib.roadmap_state import load_fragments` → returns objects with `.id`, `.kind`, `.file_path`, `.phase_refs` (verified in Step 1.3 `_check_frontmatter`)
- `Fragment.kind == "phase"` (filter value) consistent across Tasks 1 + 2
- `Phase.id` strings prefixed `phase-N(.M)?` — regex `phase-\d+(?:\.\d+)?` matches (verified in Step 2.3)

All consistent.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-07-add-roadmap-phases-and-md-integrity-category.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per Task, review between tasks, fast iteration
2. **Inline Execution** — execute tasks in this session using executing-plans, batch with checkpoints

Which approach?