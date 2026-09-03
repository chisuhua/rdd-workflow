# rdd-planner Stage 2: Sync + Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `rdd-planner` skill as a horizontal orchestrator with `status` + `sync` commands (MVP), maintaining `.rddf/state/.planner-state.json` and the AUTO-SPRINT block in `.rddf/roadmap.md`. Read-only on `.rddf/improvements/*.md` (Stage 1 ADR-0037 contract).

**Architecture:** Three new modules — `planner_state.py` (atomic state I/O), `planner_sync.py` (discover/render/apply), `planner_cmd.py` (CLI dispatch). Reuses `_lib/roadmap_sprint.py` for AUTO-SPRINT rendering, `_lib/feedback_appender.py` (read-only) for feedback status, `_lib/core/atomic_write` + `FileLock` for safety.

**Tech Stack:** Python 3.11+, PyYAML>=6.0, jsonschema>=4.0, pytest>=7.0, bats-core>=1.10.

**Spec:** `docs/superpowers/specs/2026-09-03-rdd-planner-stage2-design.md`
**Builds on:** Stage 1 (ADR-0037 feedback contract, `_lib/feedback_appender.py`).

---

## File Structure

**New files** (created in this change):
| Path | Responsibility |
|------|----------------|
| `_lib/schemas/planner_state_schema.json` | JSON schema v1 for `.planner-state.json` |
| `_lib/planner_state.py` | Atomic read/write of planner state + lock + schema validation |
| `_lib/planner_sync.py` | Discover improvements, render state, dual-zone roadmap write |
| `_lib/cli/planner_cmd.py` | `cmd_planner(args) -> int` dispatcher (status / sync subcommands) |
| `tests/unit/test_planner_state.py` | pytest unit tests (≥8) |
| `tests/unit/test_planner_sync.py` | pytest unit tests (≥12) |
| `tests/unit/test_planner_cli.py` | pytest unit tests (≥5) |
| `tests/integration/test_planner_cmd.bats` | bats CLI integration (≥5) |
| `docs/adr/ADR-0038-rdd-planner-crosscutting.md` | New ADR documenting the skill position |

**Modified files**:
| Path | Change |
|------|--------|
| `_lib/cli/__init__.py` | Register `"planner"` subcommand in `_ROUTES` dict |

**Unchanged**: All 226 existing `.rddf/improvements/*.md` files, existing roadmap.md Phase Skeleton, all 32 existing CLI subcommands.

---

## Task 1: Create `planner_state_schema.json` v1

**Files:**
- Create: `_lib/schemas/planner_state_schema.json`

- [ ] **Step 1: Write the schema file**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://rdd-workflow.local/schemas/planner_state_schema.json",
  "title": "PlannerState",
  "type": "object",
  "required": ["version", "current_sprint", "last_sync_at"],
  "properties": {
    "version": {"const": 1},
    "current_sprint": {"type": "string", "pattern": "^sprint-[0-9]{4}-[0-9]{2}$"},
    "sprint_started_at": {"type": "string", "format": "date-time"},
    "last_sync_at": {"type": "string", "format": "date-time"},
    "last_sync_status": {"type": "string", "enum": ["ok", "warn", "error"]},
    "active_projects": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["project_id", "phase", "priority", "status"],
        "properties": {
          "project_id": {"type": "string"},
          "phase": {"type": "string"},
          "theme": {"type": "string"},
          "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
          "status": {"type": "string", "enum": ["active", "blocked", "completed"]},
          "proposal": {"type": "string"},
          "change": {"type": "string"},
          "feedback_status": {"type": "string", "enum": ["none", "needs-revision", "rejected", "resolved"]},
          "last_feedback_id": {"type": "string"}
        }
      }
    },
    "unmapped_proposals": {
      "type": "array",
      "items": {"type": "string"}
    },
    "synced_proposals": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "additionalProperties": false
}
```

- [ ] **Step 2: Verify schema validates a valid sample**

```bash
python3 -c "
import json, jsonschema
schema = json.load(open('_lib/schemas/planner_state_schema.json'))
sample = {
    'version': 1,
    'current_sprint': 'sprint-2026-09',
    'last_sync_at': '2026-09-03T10:30:00+08:00',
    'active_projects': [],
    'unmapped_proposals': [],
    'synced_proposals': []
}
jsonschema.validate(sample, schema)
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3: Verify schema rejects wrong version**

```bash
python3 -c "
import json, jsonschema
schema = json.load(open('_lib/schemas/planner_state_schema.json'))
bad = {'version': 2, 'current_sprint': 'sprint-2026-09', 'last_sync_at': '2026-09-03T10:30:00+08:00'}
try:
    jsonschema.validate(bad, schema)
    print('FAIL: should have raised')
except jsonschema.ValidationError as e:
    print('OK:', e.message)
"
```

Expected: `OK: 2 was expected` (or similar).

- [ ] **Step 4: Commit**

```bash
git add _lib/schemas/planner_state_schema.json
git commit -m "feat(planner): add planner_state_schema.json v1"
```

---

## Task 2: Create `planner_state.py` skeleton + first 4 tests

**Files:**
- Create: `_lib/planner_state.py` (skeleton)
- Create: `tests/unit/test_planner_state.py` (first 4 tests)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_planner_state.py`:

```python
"""Tests for planner_state (atomic state I/O)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _lib.planner_state import (
    PlannerStateError,
    SchemaMismatchError,
    current_sprint_id,
    read_state,
    write_state,
    STATE_FILENAME,
    SCHEMA_VERSION,
)


def test_current_sprint_id_format():
    """current_sprint_id returns YYYY-MM sprint id."""
    sid = current_sprint_id()
    import re
    assert re.match(r"^sprint-\d{4}-\d{2}$", sid)


def test_read_state_returns_empty_when_missing(tmp_path):
    """read_state on missing file returns default empty state."""
    state = read_state(tmp_path)
    assert state["version"] == 1
    assert state["current_sprint"].startswith("sprint-")
    assert state["active_projects"] == []


def test_write_then_read_state_roundtrip(tmp_path):
    """write_state then read_state returns identical dict."""
    sample = {
        "version": 1,
        "current_sprint": "sprint-2026-09",
        "last_sync_at": "2026-09-03T10:30:00+08:00",
        "active_projects": [
            {
                "project_id": "foo",
                "phase": "phase-2",
                "priority": "P1",
                "status": "active",
            }
        ],
        "unmapped_proposals": ["bar"],
        "synced_proposals": ["foo"],
    }
    write_state(tmp_path, sample)
    loaded = read_state(tmp_path)
    assert loaded == sample
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_planner_state.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named '_lib.planner_state'`.

- [ ] **Step 3: Write the minimal implementation**

Create `_lib/planner_state.py`:

```python
"""Planner state I/O — atomic read/write of .rddf/state/.planner-state.json.

This module is the single source of truth for `rdd-planner` runtime
state. All writes are atomic via `_lib.core.atomic_write` and
serialized via `_lib.core.lock.FileLock` to prevent the corruption
mode seen in `.rddf/state/iteration.corrupt.*`.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema

from _lib.core.atomic_write import atomic_write_json
from _lib.core.lock import FileLock

__all__ = [
    "PlannerStateError",
    "SchemaMismatchError",
    "current_sprint_id",
    "read_state",
    "write_state",
    "STATE_FILENAME",
    "SCHEMA_VERSION",
    "STATE_SCHEMA_PATH",
]

STATE_FILENAME = ".planner-state.json"
STATE_SCHEMA_PATH = Path(__file__).parent / "schemas" / "planner_state_schema.json"
SCHEMA_VERSION = 1


class PlannerStateError(Exception):
    """Base error for planner_state."""


class SchemaMismatchError(PlannerStateError):
    """State file version does not match SCHEMA_VERSION."""


def current_sprint_id() -> str:
    """Return current sprint id (sprint-YYYY-MM) based on local time."""
    now = _dt.datetime.now()
    return f"sprint-{now.year:04d}-{now.month:02d}"


def _state_path(project_root: Path) -> Path:
    return project_root / ".rddf" / "state" / STATE_FILENAME


def _default_state() -> Dict[str, Any]:
    """Return a fresh, empty state dict."""
    return {
        "version": SCHEMA_VERSION,
        "current_sprint": current_sprint_id(),
        "last_sync_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "last_sync_status": "ok",
        "active_projects": [],
        "unmapped_proposals": [],
        "synced_proposals": [],
    }


def read_state(project_root: Path, *, validate: bool = True) -> Dict[str, Any]:
    """Read planner state. Returns default empty state if file missing.

    Args:
        project_root: Absolute path to project root.
        validate: If True (default), validate against schema after load.

    Returns:
        State dict.

    Raises:
        SchemaMismatchError: If state version != SCHEMA_VERSION.
    """
    path = _state_path(project_root)
    if not path.exists():
        return _default_state()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("version") != SCHEMA_VERSION:
        raise SchemaMismatchError(
            f"State version {data.get('version')} != expected {SCHEMA_VERSION}. "
            f"Delete {path} to reset."
        )
    if validate:
        schema = json.loads(STATE_SCHEMA_PATH.read_text())
        jsonschema.validate(data, schema)
    return data


def write_state(project_root: Path, state: Dict[str, Any], *, validate: bool = True) -> None:
    """Atomically write planner state.

    Args:
        project_root: Absolute path to project root.
        state: State dict (must conform to schema).
        validate: If True (default), validate before write.

    Raises:
        PlannerStateError: Validation failure.
    """
    if validate:
        schema = json.loads(STATE_SCHEMA_PATH.read_text())
        try:
            jsonschema.validate(state, schema)
        except jsonschema.ValidationError as exc:
            raise PlannerStateError(f"State validation failed: {exc.message}") from exc

    path = _state_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")

    with FileLock(str(lock_path), timeout=10.0):
        atomic_write_json(path, state)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_planner_state.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add _lib/planner_state.py tests/unit/test_planner_state.py
git commit -m "feat(planner-state): atomic read/write of planner state with schema validation"
```

---

## Task 3: Add remaining planner_state tests

**Files:**
- Modify: `tests/unit/test_planner_state.py` (append 5 more tests)

- [ ] **Step 1: Append 5 more tests**

```python
def test_write_state_validates_against_schema(tmp_path):
    """write_state rejects invalid data."""
    bad = {"version": 1, "current_sprint": "not-a-sprint-id", "last_sync_at": "2026-09-03T10:30:00+08:00"}
    with pytest.raises(PlannerStateError, match="validation failed"):
        write_state(tmp_path, bad)


def test_read_state_rejects_wrong_version(tmp_path):
    """read_state raises SchemaMismatchError for v2 state."""
    state_path = tmp_path / ".rddf" / "state" / STATE_FILENAME
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps({"version": 2, "current_sprint": "sprint-2026-09", "last_sync_at": "2026-09-03T10:30:00+08:00"}))
    with pytest.raises(SchemaMismatchError, match="version 2"):
        read_state(tmp_path)


def test_write_state_creates_parent_directory(tmp_path):
    """write_state creates .rddf/state/ if missing."""
    sample = {"version": 1, "current_sprint": "sprint-2026-09", "last_sync_at": "2026-09-03T10:30:00+08:00"}
    write_state(tmp_path, sample)
    expected = tmp_path / ".rddf" / "state" / STATE_FILENAME
    assert expected.exists()


def test_write_state_atomic_creates_lock_file(tmp_path):
    """write_state acquires FileLock during write."""
    import _lib.planner_state as state_mod
    sample = {"version": 1, "current_sprint": "sprint-2026-09", "last_sync_at": "2026-09-03T10:30:00+08:00"}
    called = []
    original = state_mod.FileLock
    def spy(*args, **kw):
        called.append(args)
        return original(*args, **kw)
    state_mod.FileLock = spy
    try:
        write_state(tmp_path, sample)
    finally:
        state_mod.FileLock = original
    assert any(str(tmp_path / ".rddf" / "state" / ".planner-state.json.lock") in str(a) for a in called)


def test_default_state_has_all_required_fields(tmp_path):
    """_default_state contains all required schema fields."""
    state = read_state(tmp_path)
    assert state["version"] == 1
    assert "current_sprint" in state
    assert "last_sync_at" in state
    assert isinstance(state["active_projects"], list)
    assert isinstance(state["unmapped_proposals"], list)
    assert isinstance(state["synced_proposals"], list)
```

- [ ] **Step 2: Run all planner_state tests**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_planner_state.py -v
```

Expected: 8 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_planner_state.py
git commit -m "test(planner-state): cover validation, version mismatch, lock, defaults"
```

---

## Task 4: Create `planner_sync.py` skeleton + first 4 tests

**Files:**
- Create: `_lib/planner_sync.py` (skeleton)
- Create: `tests/unit/test_planner_sync.py` (first 4 tests)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_planner_sync.py`:

```python
"""Tests for planner_sync (discover + render + apply)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _lib.planner_sync import (
    SyncError,
    discover_projects,
    parse_feedback_status,
    render_state,
)


def _make_improvement(parent: Path, name: str, *, priority: str = "P2", roadmap_ref: dict | None = None, feedback_block: str = ""):
    imp_dir = parent / ".rddf" / "improvements"
    imp_dir.mkdir(parents=True, exist_ok=True)
    f = imp_dir / f"{name}.md"
    fm = f"---\nname: {name}\npriority: {priority}\n"
    if roadmap_ref:
        fm += f"roadmap_ref: {json.dumps(roadmap_ref)}\n"
    fm += "---\n# proposal\n"
    if feedback_block:
        fm += "\n## Feedback\n\n" + feedback_block
    f.write_text(fm)
    return f


def test_discover_projects_returns_all_improvements(tmp_path):
    """discover_projects scans all *.md in .rddf/improvements/."""
    _make_improvement(tmp_path, "foo")
    _make_improvement(tmp_path, "bar")
    projects = discover_projects(tmp_path)
    names = {p["proposal"] for p in projects}
    assert names == {"foo", "bar"}


def test_discover_projects_extracts_roadmap_ref(tmp_path):
    """discover_projects reads frontmatter.roadmap_ref when present."""
    _make_improvement(tmp_path, "mapped", roadmap_ref={"project_id": "p1", "phase": "phase-2", "theme": "t1"})
    projects = discover_projects(tmp_path)
    p = next(p for p in projects if p["proposal"] == "mapped")
    assert p["project_id"] == "p1"
    assert p["phase"] == "phase-2"
    assert p["theme"] == "t1"
    assert p["mapped"] is True


def test_discover_projects_marks_unmapped(tmp_path):
    """discover_projects flags proposals without roadmap_ref as mapped=False."""
    _make_improvement(tmp_path, "unmapped")
    projects = discover_projects(tmp_path)
    p = next(p for p in projects if p["proposal"] == "unmapped")
    assert p["mapped"] is False
    assert p["phase"] == "unmapped"


def test_parse_feedback_status_returns_none_when_no_feedback(tmp_path):
    """parse_feedback_status returns 'none' when ## Feedback section absent."""
    f = _make_improvement(tmp_path, "x")
    assert parse_feedback_status(f) == "none"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_planner_sync.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named '_lib.planner_sync'`.

- [ ] **Step 3: Write the minimal implementation**

Create `_lib/planner_sync.py`:

```python
"""Planner sync — discover improvements, render state, dual-zone roadmap write.

This module is the **read-heavy** worker for `rdd-planner`. It scans
.rddf/improvements/*.md (read-only, never modifies), computes the
planner state, and (when --apply) writes:

  - .rddf/state/.planner-state.json  (atomic)
  - .rddf/roadmap.md  (dual-zone: only the AUTO-SPRINT block)

All improvement files are NEVER modified (Stage 1 ADR-0037 contract).
"""
from __future__ import annotations

import datetime as _dt
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from _lib.core.atomic_write import atomic_write_text
from _lib.core.lock import FileLock

__all__ = [
    "SyncError",
    "discover_projects",
    "parse_feedback_status",
    "render_state",
    "apply_state",
]

AUTO_SPRINT_START = "<!-- AUTO-SPRINT-START -->"
AUTO_SPRINT_END = "<!-- AUTO-SPRINT-END -->"
SPRINT_HEADER_PREFIX = "## Current Sprint:"


class SyncError(Exception):
    """Base error for planner_sync."""


def _improvements_dir(project_root: Path) -> Path:
    return project_root / ".rddf" / "improvements"


def _parse_frontmatter(text: str) -> Optional[Dict[str, Any]]:
    """Return frontmatter dict or None if absent/malformed."""
    if not text.startswith("---"):
        return None
    try:
        end = text.index("\n---", 3)
        fm_inner = text[3:end].lstrip("\n")
    except ValueError:
        return None
    try:
        return yaml.safe_load(fm_inner) or {}
    except yaml.YAMLError:
        return None


def parse_feedback_status(proposal_path: Path) -> str:
    """Derive feedback_status from ## Feedback section.

    Returns one of: 'none' | 'needs-revision' | 'rejected' | 'resolved'.
    Defaults to 'none' when no ## Feedback section exists.
    """
    if not proposal_path.exists():
        return "none"
    text = proposal_path.read_text(encoding="utf-8")
    if "## Feedback" not in text:
        return "none"
    feedback_section = text[text.index("## Feedback"):]
    if re.search(r"\*\*kind\*\*: needs-revision", feedback_section):
        return "needs-revision"
    if re.search(r"\*\*kind\*\*: rejected", feedback_section):
        return "rejected"
    if re.search(r"\*\*kind\*\*: ac-fail", feedback_section):
        return "needs-revision"
    if re.search(r"\*\*resolution\*\*: resolved", feedback_section):
        return "resolved"
    return "needs-revision"


def discover_projects(project_root: Path) -> List[Dict[str, Any]]:
    """Scan .rddf/improvements/*.md and return list of project dicts."""
    imp_dir = _improvements_dir(project_root)
    if not imp_dir.exists():
        return []
    records = []
    for f in sorted(imp_dir.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text) or {}
        ref = fm.get("roadmap_ref") or {}
        record = {
            "proposal": f.stem,
            "project_id": ref.get("project_id") if isinstance(ref, dict) else None,
            "phase": ref.get("phase") if isinstance(ref, dict) else None,
            "theme": ref.get("theme") if isinstance(ref, dict) else None,
            "priority": fm.get("priority", "P2"),
            "proposal_path": str(f),
            "feedback_status": parse_feedback_status(f),
            "mapped": bool(isinstance(ref, dict) and ref.get("project_id")),
        }
        records.append(record)
    return records


def render_state(
    project_root: Path,
    *,
    current_sprint: Optional[str] = None,
    sprint_started_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute planner state from project_root.

    Returns a dict conforming to planner_state_schema.json.
    """
    projects = discover_projects(project_root)
    active = []
    unmapped = []
    synced = []
    for p in projects:
        synced.append(p["proposal"])
        if p["mapped"]:
            active.append({
                "project_id": p["project_id"],
                "phase": p["phase"],
                "theme": p["theme"] or "",
                "priority": p["priority"],
                "status": "active",
                "proposal": p["proposal"],
                "feedback_status": p["feedback_status"],
            })
        else:
            unmapped.append(p["proposal"])

    now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    return {
        "version": 1,
        "current_sprint": current_sprint or f"sprint-{_dt.datetime.now().strftime('%Y-%m')}",
        "sprint_started_at": sprint_started_at or now,
        "last_sync_at": now,
        "last_sync_status": "ok" if not unmapped else "warn",
        "active_projects": active,
        "unmapped_proposals": unmapped,
        "synced_proposals": synced,
    }


def apply_state(project_root: Path, state: Dict[str, Any]) -> Dict[str, int]:
    """Apply state: write .planner-state.json and update AUTO-SPRINT block.

    Returns a dict of {'state_written': bool, 'roadmap_written': bool}.
    """
    from _lib.planner_state import write_state, _state_path  # local import to avoid cycle
    write_state(project_root, state)

    roadmap_path = project_root / ".rddf" / "roadmap.md"
    if roadmap_path.exists():
        roadmap_text = roadmap_path.read_text(encoding="utf-8")
        new_block = _render_sprint_block(state)
        updated = _merge_sprint_block(roadmap_text, new_block)
        with FileLock(str(roadmap_path.with_suffix(".lock")), timeout=10.0):
            atomic_write_text(roadmap_path, updated)

    return {"state_written": 1, "roadmap_written": 1 if roadmap_path.exists() else 0}


def _render_sprint_block(state: Dict[str, Any]) -> str:
    """Render the inner content of the AUTO-SPRINT block (no sentinels)."""
    lines = [f"{SPRINT_HEADER_PREFIX} {state['current_sprint']}", ""]
    if state["active_projects"]:
        lines.append("| Project | Phase | Priority | Feedback | Proposal |")
        lines.append("|---------|-------|----------|----------|----------|")
        for p in state["active_projects"]:
            lines.append(
                f"| {p['project_id']} | {p['phase']} | {p['priority']} | "
                f"{p['feedback_status']} | {p['proposal']} |"
            )
    else:
        lines.append("_No active projects in current sprint._")
    lines.append("")
    if state["unmapped_proposals"]:
        lines.append(f"### Unmapped ({len(state['unmapped_proposals'])})")
        for name in state["unmapped_proposals"][:10]:
            lines.append(f"- {name}")
        if len(state["unmapped_proposals"]) > 10:
            lines.append(f"- ... and {len(state['unmapped_proposals']) - 10} more")
        lines.append("")
    return "\n".join(lines)


def _merge_sprint_block(roadmap_text: str, new_block: str) -> str:
    """Insert or replace the AUTO-SPRINT block in roadmap_text.

    - If both sentinels present: replace content between them.
    - If only start sentinel: insert end sentinel and replace.
    - If neither: append after '## Phase Skeleton' table (idempotent first-run).
    """
    start_idx = roadmap_text.find(AUTO_SPRINT_START)
    end_idx = roadmap_text.find(AUTO_SPRINT_END)

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        before = roadmap_text[:start_idx + len(AUTO_SPRINT_START)]
        after = roadmap_text[end_idx:]
        return f"{before}\n{new_block}\n{after}"

    if start_idx != -1 and end_idx == -1:
        before = roadmap_text[:start_idx + len(AUTO_SPRINT_START)]
        return f"{before}\n{new_block}\n{AUTO_SPRINT_END}\n"

    if "## Phase Skeleton" in roadmap_text and "<!-- AUTO-INDEX -->" in roadmap_text:
        idx = roadmap_text.index("<!-- AUTO-INDEX -->")
        before = roadmap_text[:idx].rstrip() + "\n\n"
        after = "\n" + roadmap_text[idx:]
        return f"{before}{AUTO_SPRINT_START}\n{new_block}\n{AUTO_SPRINT_END}\n{after}"

    return f"{roadmap_text.rstrip()}\n\n{AUTO_SPRINT_START}\n{new_block}\n{AUTO_SPRINT_END}\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_planner_sync.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add _lib/planner_sync.py tests/unit/test_planner_sync.py
git commit -m "feat(planner-sync): discover improvements, render state, dual-zone roadmap write"
```

---

## Task 5: Add remaining planner_sync tests

**Files:**
- Modify: `tests/unit/test_planner_sync.py` (append 8 more tests)

- [ ] **Step 1: Append 8 more tests**

```python
def test_parse_feedback_status_detects_needs_revision(tmp_path):
    """parse_feedback_status returns 'needs-revision' when ## Feedback has that kind."""
    f = _make_improvement(tmp_path, "x", feedback_block="### fb\n- **kind**: needs-revision\n- **resolution**: open\n")
    assert parse_feedback_status(f) == "needs-revision"


def test_parse_feedback_status_detects_rejected(tmp_path):
    f = _make_improvement(tmp_path, "x", feedback_block="### fb\n- **kind**: rejected\n- **resolution**: open\n")
    assert parse_feedback_status(f) == "rejected"


def test_parse_feedback_status_detects_ac_fail(tmp_path):
    f = _make_improvement(tmp_path, "x", feedback_block="### fb\n- **kind**: ac-fail\n- **resolution**: open\n")
    assert parse_feedback_status(f) == "needs-revision"


def test_render_state_returns_valid_dict(tmp_path):
    """render_state returns a dict with all required keys."""
    _make_improvement(tmp_path, "foo", roadmap_ref={"project_id": "p1", "phase": "phase-2", "theme": "t"})
    state = render_state(tmp_path)
    assert state["version"] == 1
    assert state["current_sprint"].startswith("sprint-")
    assert isinstance(state["active_projects"], list)
    assert len(state["active_projects"]) == 1
    assert state["active_projects"][0]["project_id"] == "p1"


def test_render_state_separates_unmapped(tmp_path):
    """render_state populates unmapped_proposals for files without roadmap_ref."""
    _make_improvement(tmp_path, "unmapped1")
    _make_improvement(tmp_path, "unmapped2")
    _make_improvement(tmp_path, "mapped", roadmap_ref={"project_id": "p1", "phase": "phase-1"})
    state = render_state(tmp_path)
    assert set(state["unmapped_proposals"]) == {"unmapped1", "unmapped2"}
    assert len(state["active_projects"]) == 1


def test_render_state_warn_when_unmapped(tmp_path):
    """render_state sets last_sync_status=warn when unmapped proposals exist."""
    _make_improvement(tmp_path, "u1")
    state = render_state(tmp_path)
    assert state["last_sync_status"] == "warn"


def test_render_state_ok_when_all_mapped(tmp_path):
    """render_state sets last_sync_status=ok when no unmapped proposals."""
    _make_improvement(tmp_path, "m", roadmap_ref={"project_id": "p", "phase": "phase-1"})
    state = render_state(tmp_path)
    assert state["last_sync_status"] == "ok"


def test_apply_state_writes_planner_state_and_roadmap(tmp_path):
    """apply_state writes both .planner-state.json and updates roadmap.md."""
    _make_improvement(tmp_path, "x", roadmap_ref={"project_id": "p", "phase": "phase-1"})
    roadmap = tmp_path / ".rddf" / "roadmap.md"
    roadmap.write_text("# Roadmap\n\n## Phase Skeleton\n| Phase | Theme |\n|-------|-------|\n| phase-1 | t |\n\n<!-- AUTO-INDEX -->\n")
    state = render_state(tmp_path)
    apply_state(tmp_path, state)
    assert (tmp_path / ".rddf" / "state" / ".planner-state.json").exists()
    updated = roadmap.read_text()
    assert "<!-- AUTO-SPRINT-START -->" in updated
    assert "<!-- AUTO-SPRINT-END -->" in updated
    assert "Phase Skeleton" in updated
```

- [ ] **Step 2: Run all planner_sync tests**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_planner_sync.py -v
```

Expected: 12 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_planner_sync.py
git commit -m "test(planner-sync): cover feedback parsing, render, apply, dual-zone write"
```

---

## Task 6: Create `planner_cmd.py` skeleton + 3 tests

**Files:**
- Create: `_lib/cli/planner_cmd.py` (skeleton)
- Create: `tests/unit/test_planner_cli.py` (first 3 tests)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_planner_cli.py`:

```python
"""Tests for planner CLI dispatcher."""
from __future__ import annotations

import json
import pytest

from _lib.cli.planner_cmd import cmd_planner


def test_cli_status_prints_sprint_info(tmp_path, capsys):
    """rddf planner status prints sprint id."""
    rc = cmd_planner(["status", "--project-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "sprint-" in captured.out


def test_cli_sync_default_is_dry_run(tmp_path, capsys):
    """rddf planner sync without --apply does NOT write state file."""
    rc = cmd_planner(["sync", "--project-root", str(tmp_path)])
    assert rc == 0
    state_path = tmp_path / ".rddf" / "state" / ".planner-state.json"
    assert not state_path.exists()


def test_cli_sync_apply_writes_state(tmp_path, capsys):
    """rddf planner sync --apply writes state file."""
    rc = cmd_planner(["sync", "--apply", "--project-root", str(tmp_path)])
    assert rc == 0
    state_path = tmp_path / ".rddf" / "state" / ".planner-state.json"
    assert state_path.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_planner_cli.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named '_lib.cli.planner_cmd'`.

- [ ] **Step 3: Write the minimal implementation**

Create `_lib/cli/planner_cmd.py`:

```python
"""CLI dispatcher for `rddf planner ...` subcommands (Stage 2 MVP).

Subcommands:
  status                    read-only sprint snapshot
  sync [--apply] [--dry-run]  default --dry-run; --apply writes state
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from _lib.planner_state import PlannerStateError, read_state, write_state
from _lib.planner_sync import apply_state, render_state


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rddf planner",
        description="Manage rdd-planner sprint state (horizontal orchestrator, per ADR-0038).",
    )
    parser.add_argument("--project-root", default=".", help="Project root (default: cwd)")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    sub.add_parser("status", help="Print sprint snapshot")

    p_sync = sub.add_parser("sync", help="Sync state (default: dry-run)")
    p_sync.add_argument("--apply", action="store_true", help="Actually write state and roadmap")
    p_sync.add_argument("--dry-run", action="store_true", help="Force dry-run (default)")

    return parser


def cmd_planner(args: List[str]) -> int:
    parser = _build_parser()
    ns = parser.parse_args(args)
    project_root = Path(ns.project_root).resolve()

    try:
        if ns.subcommand == "status":
            try:
                state = read_state(project_root)
                source = "stored"
            except (PlannerStateError, Exception):
                state = render_state(project_root)
                source = "computed"
            sys.stdout.write(f"Sprint: {state['current_sprint']}\n")
            sys.stdout.write(f"Source: {source}\n")
            sys.stdout.write(f"Active projects: {len(state['active_projects'])}\n")
            sys.stdout.write(f"Unmapped proposals: {len(state['unmapped_proposals'])}\n")
            sys.stdout.write(f"Status: {state.get('last_sync_status', 'unknown')}\n")
            return 0

        if ns.subcommand == "sync":
            apply = ns.apply
            state = render_state(project_root)
            if not apply:
                sys.stdout.write(f"DRY-RUN: would write state and update roadmap.\n")
                sys.stdout.write(f"  Sprint: {state['current_sprint']}\n")
                sys.stdout.write(f"  Active: {len(state['active_projects'])}\n")
                sys.stdout.write(f"  Unmapped: {len(state['unmapped_proposals'])}\n")
                sys.stdout.write(f"  Run with --apply to write.\n")
                return 0
            apply_state(project_root, state)
            sys.stdout.write(f"✓ State written\n")
            sys.stdout.write(f"  Sprint: {state['current_sprint']}\n")
            return 0

        parser.print_help()
        return 1

    except PlannerStateError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1
    except FileNotFoundError as exc:
        sys.stderr.write(f"FILE NOT FOUND: {exc}\n")
        return 2
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_planner_cli.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add _lib/cli/planner_cmd.py tests/unit/test_planner_cli.py
git commit -m "feat(planner-cmd): CLI dispatcher with status and sync subcommands"
```

---

## Task 7: Add 2 more CLI tests

**Files:**
- Modify: `tests/unit/test_planner_cli.py` (append 2 tests)

- [ ] **Step 1: Append 2 more tests**

```python
def test_cli_status_with_stored_state(tmp_path, capsys):
    """status reads stored state if it exists."""
    from _lib.planner_state import write_state
    sample = {
        "version": 1,
        "current_sprint": "sprint-2026-09",
        "last_sync_at": "2026-09-03T10:30:00+08:00",
        "active_projects": [],
        "unmapped_proposals": [],
        "synced_proposals": [],
    }
    write_state(tmp_path, sample)
    rc = cmd_planner(["status", "--project-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "stored" in captured.out
    assert "sprint-2026-09" in captured.out


def test_cli_no_subcommand_exits_nonzero(capsys):
    """argparse exits 2 when no subcommand given."""
    try:
        rc = cmd_planner([])
        assert rc != 0
    except SystemExit as e:
        assert e.code != 0
```

- [ ] **Step 2: Run all CLI tests**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_planner_cli.py -v
```

Expected: 5 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_planner_cli.py
git commit -m "test(planner-cmd): cover stored state and missing subcommand"
```

---

## Task 8: Register `planner` in `_lib/cli/__init__.py`

**Files:**
- Modify: `_lib/cli/__init__.py` (add 1 line to `_ROUTES`)

- [ ] **Step 1: Add the route**

In `_lib/cli/__init__.py`, find the `_ROUTES` dict and add a new entry after `"l2-trend"`:

```python
    "l2-trend": "skills._lib.cli.l2_trend_cmd:cmd_l2_trend",
    "planner": "skills._lib.cli.planner_cmd:cmd_planner",
    "monitor": "skills._lib.cli.monitor_cmd:cmd_monitor",
```

- [ ] **Step 2: Verify route resolves**

Run:
```bash
python3 -c "
from _lib.cli import list_commands
assert 'planner' in list_commands(), 'planner not in routes'
print('OK: planner registered')
print('Total commands:', len(list_commands()))
"
```

Expected: `OK: planner registered` and `Total commands: 33`.

- [ ] **Step 3: Commit**

```bash
git add _lib/cli/__init__.py
git commit -m "feat(planner-cmd): register 'planner' in _lib/cli _ROUTES"
```

---

## Task 9: Write bats integration tests

**Files:**
- Create: `tests/integration/test_planner_cmd.bats`

- [ ] **Step 1: Write the bats test file**

Create `tests/integration/test_planner_cmd.bats`:

```bash
#!/usr/bin/env bats
# Integration tests for `rddf planner` CLI.

load test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/improvements"
    mkdir -p "$TEST_TMP/.rddf/state"
    cd "$TEST_TMP"
    git init -q .
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "planner: status prints sprint id" {
    run python3 -m _lib.cli planner status --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "sprint-" ]]
}

@test "planner: sync dry-run does not write state" {
    cat > .rddf/improvements/foo.md <<'EOF'
---
name: foo
priority: P2
roadmap_ref:
  project_id: foo-impl
  phase: phase-2
  theme: foo theme
---
# foo
EOF

    run python3 -m _lib.cli planner sync --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "DRY-RUN" ]]
    [ ! -f .rddf/state/.planner-state.json ]
}

@test "planner: sync --apply writes state and roadmap" {
    cat > .rddf/improvements/foo.md <<'EOF'
---
name: foo
priority: P2
roadmap_ref:
  project_id: foo-impl
  phase: phase-2
  theme: foo theme
---
# foo
EOF
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap

## Phase Skeleton
| Phase | Theme |
|-------|-------|
| phase-1 | t |

<!-- AUTO-INDEX -->
EOF

    run python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [ -f .rddf/state/.planner-state.json ]
    grep -q "AUTO-SPRINT-START" .rddf/roadmap.md
    grep -q "AUTO-SPRINT-END" .rddf/roadmap.md
    grep -q "Phase Skeleton" .rddf/roadmap.md
}

@test "planner: sync preserves Phase Skeleton table" {
    cat > .rddf/roadmap.md <<'EOF'
# Roadmap

## Phase Skeleton
| Phase | Theme |
|-------|-------|
| phase-1 | manual theme |

<!-- AUTO-INDEX -->
EOF

    python3 -m _lib.cli planner sync --apply --project-root "$TEST_TMP"

    grep -q "manual theme" .rddf/roadmap.md
}

@test "planner: status reads stored state" {
    mkdir -p .rddf/state
    cat > .rddf/state/.planner-state.json <<'EOF'
{
  "version": 1,
  "current_sprint": "sprint-2026-09",
  "last_sync_at": "2026-09-03T10:30:00+08:00",
  "active_projects": [],
  "unmapped_proposals": [],
  "synced_proposals": []
}
EOF

    run python3 -m _lib.cli planner status --project-root "$TEST_TMP"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "stored" ]]
    [[ "$output" =~ "sprint-2026-09" ]]
}
```

- [ ] **Step 2: Run bats integration tests**

Run:
```bash
bats tests/integration/test_planner_cmd.bats
```

Expected: 5 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_planner_cmd.bats
git commit -m "test(planner-cmd): 5 bats integration tests covering status, sync, dual-zone"
```

---

## Task 10: Write ADR-0038

**Files:**
- Create: `docs/adr/ADR-0038-rdd-planner-crosscutting.md`

- [ ] **Step 1: Write the ADR**

Create the file with this content:

```markdown
# ADR-0038: rdd-planner Horizontal Orchestrator (Stage 2)

## Status

Accepted (2026-09-03) — Stage 2 of `rdd-planner` design, implemented per
`docs/superpowers/specs/2026-09-03-rdd-planner-stage2-design.md`.

## Context

After Stage 1 (ADR-0037 feedback contract) shipped, the codebase has:

- 226 `.rddf/improvements/*.md` files (mostly without `roadmap_ref`)
- `.rddf/roadmap.md` with manual Phase Skeleton but no AUTO-SPRINT block
- No central state for sprint progress or proposal↔roadmap mapping
- 30+ `iteration.corrupt.*` residual files (Oracle review evidence of multi-writer race risk)

A planner/orchestrator role was requested to:
- Maintain roadmap ↔ proposal mapping
- Manage sprint lifecycle
- Read feedback and trigger revisions

## Decision

Implement `rdd-planner` as a **horizontal orchestrator** (NOT a sixth phase):

1. **Position**: Cross-cutting, callable from any phase. Does NOT replace or
   extend the 5-phase architecture (arch → design → plan → ship → verify).

2. **Commands in Stage 2 MVP**:
   - `rddf planner status` — read-only sprint snapshot
   - `rddf planner sync [--apply|--dry-run]` — default dry-run

3. **State file**: New `.rddf/state/.planner-state.json` (gitignored,
   schema v1). Atomic writes via `_lib/core/atomic_write` + `FileLock`.

4. **Roadmap write strategy**: Dual-zone — preserve user-edited Phase
   Skeleton table; only overwrite the AUTO-SPRINT block (between
   `<!-- AUTO-SPRINT-START -->` and `<!-- AUTO-SPRINT-END -->` sentinels).

5. **Improvement file policy**: Read-only on `.rddf/improvements/*.md`.
   All 226 existing files continue to work without migration.

6. **Feedback integration**: Read-only consumer of Stage 1's
   `## Feedback` section via the ADR-0037 contract. No writes to
   improvement files.

## Consequences

### Positive

- ✅ Sprint concept now first-class (was implicit in roadmap_sprint.py).
- ✅ Single source of truth for active projects.
- ✅ Dual-zone write preserves user manual edits to Phase Skeleton.
- ✅ Zero migration burden on 226 existing improvement files.
- ✅ Idempotent (default dry-run; --apply writes are atomic).
- ✅ Follows 5-phase architecture (no phase pollution).

### Negative

- ⚠️ Adds ~700 lines of Python (state + sync + CLI + ~25 tests).
- ⚠️ `revise` and `audit` subcommands deferred to Stage 2.5.
- ⚠️ `--apply` requires manual flag — accidental writes are avoided but
  user must remember to add flag.

### Neutral

- Stage 3 (`rdd-arch` rename) builds on this contract.
- Stage 4 (no-merge) does not affect this contract.

## Alternatives Considered

1. **Sixth phase `rdd-planner`** — rejected (per Oracle review, 5-phase
   architecture is stable; adding a phase creates governance debt).
2. **Inline planner in `guide-arch`** — rejected (creates 2 writers of
   `.rddf/roadmap.md`, exactly the multi-writer corruption scenario).
3. **SQLite-backed state** — rejected (out of scope for Stage 2; adds
   heavy dependency for ~100 lines of JSON state).

## References

- Spec: `docs/superpowers/specs/2026-09-03-rdd-planner-stage2-design.md`
- Plan: `docs/superpowers/plans/2026-09-03-rdd-planner-stage2.md`
- ADR-0037: feedback contract (Stage 1, hard dependency)
- ADR-0028: role-model per phase
- `_lib/core/atomic_write.py` and `_lib/core/lock.py` (proven primitives)
- `_lib/roadmap_sprint.py` (AUTO-SPRINT block renderer, reused)
- `.rddf/state/iteration.corrupt.*` (the failure mode this ADR prevents)

## Supersedes

None. Additive contract. Stage 1 ADR-0037 remains in force.
```

- [ ] **Step 2: Verify ADR file is valid Markdown**

Run:
```bash
head -20 docs/adr/ADR-0038-rdd-planner-crosscutting.md
```

Expected: prints the header and status block.

- [ ] **Step 3: Commit**

```bash
git add docs/adr/ADR-0038-rdd-planner-crosscutting.md
git commit -m "docs(adr): add ADR-0038 rdd-planner horizontal orchestrator"
```

---

## Task 11: Full regression gate

**Files:** None (verification only)

- [ ] **Step 1: Run all new unit tests**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_planner_state.py tests/unit/test_planner_sync.py tests/unit/test_planner_cli.py -v
```

Expected: 25 passed (8 + 12 + 5).

- [ ] **Step 2: Run bats integration**

Run:
```bash
bats tests/integration/test_planner_cmd.bats
```

Expected: 5 passed.

- [ ] **Step 3: Run smoke regression**

Run:
```bash
bats tests/smoke.bats
```

Expected: 9 passed (no regression).

- [ ] **Step 4: Verify 226 existing improvements untouched**

Run:
```bash
git status --short .rddf/improvements/
```

Expected: empty output (no files modified).

- [ ] **Step 5: Manual demo run**

```bash
mkdir -p /tmp/planner-demo/.rddf/improvements /tmp/planner-demo/.rddf/state
cat > /tmp/planner-demo/.rddf/improvements/foo.md <<'EOF'
---
name: foo
priority: P2
roadmap_ref:
  project_id: foo-impl
  phase: phase-2
  theme: foo theme
---
# foo
EOF
cat > /tmp/planner-demo/.rddf/roadmap.md <<'EOF'
# Roadmap

## Phase Skeleton
| Phase | Theme | Status |
|-------|-------|--------|
| phase-2 | manual theme | active |

<!-- AUTO-INDEX -->
EOF

python3 -m _lib.cli planner status --project-root /tmp/planner-demo
python3 -m _lib.cli planner sync --project-root /tmp/planner-demo
python3 -m _lib.cli planner sync --apply --project-root /tmp/planner-demo
cat /tmp/planner-demo/.rddf/roadmap.md
```

Expected: status prints sprint id; sync dry-run prints preview; sync --apply writes both files; roadmap shows AUTO-SPRINT block after Phase Skeleton table (which is preserved).

- [ ] **Step 6: Final commit (if demo created files in repo)**

```bash
git status --short
# (Should show no changes; if any demo files committed, add cleanup commit)
```

---

## Self-Review

### 1. Spec coverage

| Spec Section | Task |
|--------------|------|
| §2 Decisions 1-12 | Tasks 1-10 (all 12 decisions mapped) |
| §3.1 Component diagram | Tasks 2, 4, 6 |
| §3.2 File layout | Tasks 1-10 (all 9 files) |
| §3.3 Sequence dry-run | Task 4 (render_state, discover_projects) |
| §3.4 Sequence apply | Task 4 (apply_state) |
| §3.5 Schema v1 | Task 1 |
| §3.6 Dual-zone write | Task 4 (_merge_sprint_block) |
| §3.7 Mapping algorithm | Task 4 (discover_projects) |
| §3.8 CLI surface | Task 6 (cmd_planner) |
| §4 Migration | Tasks 4, 5 (zero impact on 226 files) |
| §5 Testing | Tasks 2, 3, 4, 5, 6, 7, 9 |
| §6 Acceptance | Task 11 |
| §7 Demo | Task 11 Step 5 |
| §8 Risks | Mitigated by atomic_write + lock + dual-zone |

**Gap**: None identified. All 12 spec acceptance criteria map to a task.

### 2. Placeholder scan

- No "TBD", "TODO", "fill in", "similar to Task N" found.
- All code blocks are concrete and copy-pasteable.
- File paths are absolute or project-relative and exist.

### 3. Type consistency

- `read_state(project_root, *, validate=True) -> Dict[str, Any]` used consistently.
- `write_state(project_root, state, *, validate=True) -> None` consistent.
- `discover_projects(project_root) -> List[Dict[str, Any]]` consistent.
- `render_state(project_root, *, current_sprint=None, sprint_started_at=None) -> Dict[str, Any]` consistent.
- `apply_state(project_root, state) -> Dict[str, int]` consistent.
- `cmd_planner(args: List[str]) -> int` matches `_lib/cli/__init__.py` route signature.

### 4. Edge cases handled

- ✅ Missing `.rddf/improvements/` → returns empty list (Task 5 + Task 11 demo)
- ✅ Missing `.planner-state.json` → returns default (Task 2)
- ✅ Missing `.rddf/roadmap.md` → apply_state skips roadmap write (Task 4)
- ✅ Missing AUTO-SPRINT sentinels → first-run appends (Task 4 _merge_sprint_block)
- ✅ Schema mismatch (v2) → SchemaMismatchError (Task 3)
- ✅ Validation failure → PlannerStateError (Task 3)
- ✅ Concurrent writes → FileLock (Task 3)
- ✅ Empty projects list → `_No active projects_` row (Task 4)
- ✅ Many unmapped → truncated to 10 (Task 4)

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-09-03-rdd-planner-stage2.md`.**

11 tasks with isolated file scopes. Ready for inline execution (executing-plans).
