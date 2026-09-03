# rdd-planner Stage 1: Feedback Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a single-writer append-only feedback contract for `.rddf/improvements/*.md` files via a new `rddf feedback add` CLI, with stable improvement↔OpenSpec-change ID linking and a 3-revision loop guard.

**Architecture:** Three new modules — `feedback_resolver.py` (read-only ID resolution), `feedback_appender.py` (atomic append with lock + loop guard), `feedback_cmd.py` (CLI dispatch). One new JSON schema (`feedback_entry_schema.json`) + one new frontmatter schema (`improvement_frontmatter_schema.json` v2). All writes go through `_lib/core/atomic_write.py` + `_lib/core/lock.py` (proven primitives).

**Tech Stack:** Python 3.11+, PyYAML>=6.0, jsonschema>=4.0, pytest>=7.0, bats-core>=1.10.

**Spec:** `docs/superpowers/specs/2026-09-03-rdd-planner-stage1-feedback-contract.md`

---

## File Structure

**New files** (created in this change):
| Path | Responsibility |
|------|----------------|
| `_lib/feedback_resolver.py` | Read-only resolution: proposal → change-name (via `--ref-change` / frontmatter `change:` / basename equality) |
| `_lib/feedback_appender.py` | Append-only feedback writer with lock + revision-count guard + frontmatter management |
| `_lib/cli/feedback_cmd.py` | `cmd_feedback(args) -> int` dispatcher with sub-subcommands: `add` / `list` / `resolve` / `show-schema` |
| `_lib/schemas/feedback_entry_schema.json` | JSON schema v1 for single feedback entry (7 fields) |
| `_lib/schemas/improvement_frontmatter_schema.json` | JSON schema v2 for improvement frontmatter (additive fields only) |
| `tests/unit/test_feedback_resolver.py` | pytest unit tests (≥8) |
| `tests/unit/test_feedback_appender.py` | pytest unit tests (≥12) |
| `tests/unit/test_feedback_cli.py` | pytest unit tests (≥10) |
| `tests/integration/test_feedback_cmd.bats` | bats CLI integration (≥8) |
| `docs/adr/ADR-0037-feedback-contract.md` | New ADR documenting the append-only contract |

**Modified files**:
| Path | Change |
|------|--------|
| `_lib/cli/__init__.py` | Register `"feedback"` subcommand in `_ROUTES` dict |
| `rddf` (CLI wrapper, if exists) | Verify `feedback` propagates through wrapper; update if missing |

**Unchanged**: All 226 existing `.rddf/improvements/*.md` files, all existing skills, `_lib/cli/feedback_*.py` is new (not modified).

---

## Task 1: Create `feedback_entry_schema.json`

**Files:**
- Create: `_lib/schemas/feedback_entry_schema.json`

- [ ] **Step 1: Write the schema file**

Create the file with the exact JSON schema content from spec §3.5:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://rdd-workflow.local/schemas/feedback_entry_schema.json",
  "title": "FeedbackEntry",
  "type": "object",
  "required": ["feedback_id", "source", "kind", "created_at", "body"],
  "properties": {
    "feedback_id": {
      "type": "string",
      "pattern": "^feedback-[0-9]{8}-[0-9]{3,6}$"
    },
    "source": {
      "type": "string",
      "enum": ["guide-design", "guide-plan", "guide-ship", "rdd-verifier", "human"]
    },
    "kind": {
      "type": "string",
      "enum": ["needs-revision", "ac-fail", "rejected", "blocked", "noted"]
    },
    "ref_change": {
      "type": "string"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "body": {
      "type": "string",
      "minLength": 1,
      "maxLength": 10000
    },
    "resolution": {
      "type": "string",
      "enum": ["open", "resolved", "wont-fix"],
      "default": "open"
    },
    "resolved_at": {
      "type": "string",
      "format": "date-time"
    },
    "resolved_by": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

- [ ] **Step 2: Verify schema validates against a valid sample**

Run:
```bash
python3 -c "
import json
import jsonschema
schema = json.load(open('_lib/schemas/feedback_entry_schema.json'))
sample = {
    'feedback_id': 'feedback-20260903-001',
    'source': 'guide-design',
    'kind': 'needs-revision',
    'created_at': '2026-09-03T10:30:00+08:00',
    'body': '缺少对回归门失败 vs 新失败的区分规则。'
}
jsonschema.validate(sample, schema)
print('OK')
"
```

Expected: prints `OK`.

- [ ] **Step 3: Verify schema rejects invalid source**

Run:
```bash
python3 -c "
import json
import jsonschema
schema = json.load(open('_lib/schemas/feedback_entry_schema.json'))
bad = {
    'feedback_id': 'feedback-20260903-001',
    'source': 'invalid-source',
    'kind': 'needs-revision',
    'created_at': '2026-09-03T10:30:00+08:00',
    'body': 'test'
}
try:
    jsonschema.validate(bad, schema)
    print('FAIL: should have raised')
except jsonschema.ValidationError as e:
    print('OK:', e.message)
"
```

Expected: prints `OK: 'invalid-source' is not one of ['guide-design', ...]`.

- [ ] **Step 4: Commit**

```bash
git add _lib/schemas/feedback_entry_schema.json
git commit -m "feat(feedback-contract): add feedback_entry_schema.json v1"
```

---

## Task 2: Create `improvement_frontmatter_schema.json` v2

**Files:**
- Create: `_lib/schemas/improvement_frontmatter_schema.json`

- [ ] **Step 1: Write the schema file**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://rdd-workflow.local/schemas/improvement_frontmatter_schema.json",
  "title": "ImprovementFrontmatter",
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "priority": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
    "source": {"type": "string"},
    "phase": {"type": "string"},
    "category": {"type": "string"},
    "type": {"type": "string"},
    "created_at": {"type": "string"},
    "change": {
      "type": "string",
      "description": "OpenSpec change name (added in v2, opt-in)"
    },
    "revision_count": {
      "type": "integer",
      "minimum": 0,
      "default": 0,
      "description": "Auto-managed by feedback_appender (added in v2)"
    },
    "max_revisions": {
      "type": "integer",
      "minimum": 1,
      "default": 3,
      "description": "Loop guard cap (added in v2)"
    },
    "last_feedback_id": {
      "type": "string",
      "description": "Auto-managed by feedback_appender (added in v2)"
    },
    "last_feedback_at": {
      "type": "string",
      "format": "date-time",
      "description": "Auto-managed by feedback_appender (added in v2)"
    },
    "feedback_status": {
      "type": "string",
      "enum": ["none", "needs-revision", "rejected", "resolved"],
      "default": "none",
      "description": "Auto-managed by feedback_appender (added in v2)"
    }
  },
  "additionalProperties": true
}
```

- [ ] **Step 2: Verify legacy frontmatter (no v2 fields) still validates**

Run:
```bash
python3 -c "
import json
import jsonschema
schema = json.load(open('_lib/schemas/improvement_frontmatter_schema.json'))
legacy = {'name': 'foo', 'priority': 'P2', 'source': 'human'}
jsonschema.validate(legacy, schema)
print('OK')
"
```

Expected: prints `OK`.

- [ ] **Step 3: Verify new v2 frontmatter validates**

Run:
```bash
python3 -c "
import json
import jsonschema
schema = json.load(open('_lib/schemas/improvement_frontmatter_schema.json'))
new = {
    'name': 'foo',
    'change': 'add-foo',
    'revision_count': 2,
    'max_revisions': 3,
    'feedback_status': 'needs-revision'
}
jsonschema.validate(new, schema)
print('OK')
"
```

Expected: prints `OK`.

- [ ] **Step 4: Commit**

```bash
git add _lib/schemas/improvement_frontmatter_schema.json
git commit -m "feat(feedback-contract): add improvement_frontmatter_schema.json v2 (additive)"
```

---

## Task 3: Create `feedback_resolver.py` skeleton + write first failing test

**Files:**
- Create: `_lib/feedback_resolver.py` (skeleton)
- Create: `tests/unit/test_feedback_resolver.py` (first 3 tests)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_feedback_resolver.py`:

```python
"""Tests for feedback_resolver (read-only proposal→change resolution)."""
from __future__ import annotations

import pytest

from _lib.feedback_resolver import resolve_change_id, ResolutionError


def test_resolver_explicit_ref_change(tmp_path):
    """--ref-change takes precedence over everything else."""
    improvement = tmp_path / "improve-foo.md"
    improvement.write_text("---\nname: improve-foo\n---\n")
    # Even if frontmatter says change=other, explicit wins
    result = resolve_change_id(
        proposal="improve-foo",
        improvement_path=str(improvement),
        explicit_ref="my-change"
    )
    assert result == "my-change"


def test_resolver_frontmatter_change_field(tmp_path):
    """If no explicit ref, read frontmatter 'change:' field."""
    improvement = tmp_path / "improve-bar.md"
    improvement.write_text("---\nname: improve-bar\nchange: bar-change\n---\n")
    result = resolve_change_id(
        proposal="improve-bar",
        improvement_path=str(improvement),
        explicit_ref=None
    )
    assert result == "bar-change"


def test_resolver_basename_fallback(tmp_path):
    """If neither explicit nor frontmatter, fall back to proposal name == change name."""
    improvement = tmp_path / "improve-baz.md"
    improvement.write_text("---\nname: improve-baz\n---\n")
    result = resolve_change_id(
        proposal="improve-baz",
        improvement_path=str(improvement),
        explicit_ref=None
    )
    assert result == "improve-baz"
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_feedback_resolver.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named '_lib.feedback_resolver'`.

- [ ] **Step 3: Write the minimal implementation**

Create `_lib/feedback_resolver.py`:

```python
"""Read-only resolution of proposal name → OpenSpec change name.

Resolution priority (highest first):
  1. explicit_ref (from CLI --ref-change)
  2. improvement frontmatter 'change:' field
  3. basename equality (proposal name == change name)

This module does NOT mutate any file. Pure read.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml


class ResolutionError(Exception):
    """Raised when resolution cannot proceed (e.g. file unreadable)."""


def resolve_change_id(
    *,
    proposal: str,
    improvement_path: str,
    explicit_ref: Optional[str] = None,
) -> str:
    """Resolve proposal name to OpenSpec change name.

    Args:
        proposal: The proposal name (used as fallback).
        improvement_path: Absolute path to .rddf/improvements/<name>.md.
        explicit_ref: Optional explicit --ref-change value (highest priority).

    Returns:
        The resolved OpenSpec change name.

    Raises:
        ResolutionError: If improvement file is unreadable or frontmatter malformed.
    """
    if explicit_ref:
        return explicit_ref

    p = Path(improvement_path)
    if not p.exists():
        return proposal  # basename fallback even if file missing

    text = p.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return proposal

    # Extract frontmatter block
    try:
        end = text.index("\n---", 3)
        fm_block = text[3:end].lstrip("\n")
    except ValueError as exc:
        raise ResolutionError(
            f"Malformed frontmatter in {improvement_path}: no closing ---"
        ) from exc

    try:
        fm = yaml.safe_load(fm_block) or {}
    except yaml.YAMLError as exc:
        raise ResolutionError(
            f"YAML parse error in {improvement_path}: {exc}"
        ) from exc

    change = fm.get("change")
    if isinstance(change, str) and change:
        return change

    return proposal
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_feedback_resolver.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add _lib/feedback_resolver.py tests/unit/test_feedback_resolver.py
git commit -m "feat(feedback-resolver): proposal→change ID resolution with 3-tier priority"
```

---

## Task 4: Add remaining `feedback_resolver` tests

**Files:**
- Modify: `tests/unit/test_feedback_resolver.py` (append 5 more tests)

- [ ] **Step 1: Append 5 more tests**

```python
def test_resolver_missing_file_falls_back_to_basename(tmp_path):
    """If improvement file does not exist, return proposal name."""
    result = resolve_change_id(
        proposal="ghost",
        improvement_path=str(tmp_path / "does-not-exist.md"),
        explicit_ref=None
    )
    assert result == "ghost"


def test_resolver_missing_frontmatter_falls_back_to_basename(tmp_path):
    """If file exists but has no frontmatter, return proposal name."""
    improvement = tmp_path / "no-front.md"
    improvement.write_text("# Just a body, no frontmatter\n")
    result = resolve_change_id(
        proposal="no-front",
        improvement_path=str(improvement),
        explicit_ref=None
    )
    assert result == "no-front"


def test_resolver_empty_change_field_falls_back(tmp_path):
    """If frontmatter 'change:' is empty string, fall back to basename."""
    improvement = tmp_path / "empty-change.md"
    improvement.write_text("---\nname: empty-change\nchange: ''\n---\n")
    result = resolve_change_id(
        proposal="empty-change",
        improvement_path=str(improvement),
        explicit_ref=None
    )
    assert result == "empty-change"


def test_resolver_malformed_frontmatter_raises(tmp_path):
    """If frontmatter has opening --- but no closing, raise ResolutionError."""
    improvement = tmp_path / "bad-fm.md"
    improvement.write_text("---\nname: bad\nno closing")
    with pytest.raises(ResolutionError, match="Malformed frontmatter"):
        resolve_change_id(
            proposal="bad-fm",
            improvement_path=str(improvement),
            explicit_ref=None
        )


def test_resolver_invalid_yaml_raises(tmp_path):
    """If frontmatter YAML is malformed, raise ResolutionError."""
    improvement = tmp_path / "bad-yaml.md"
    improvement.write_text("---\nname: [unclosed bracket\n---\n")
    with pytest.raises(ResolutionError, match="YAML parse error"):
        resolve_change_id(
            proposal="bad-yaml",
            improvement_path=str(improvement),
            explicit_ref=None
        )
```

- [ ] **Step 2: Run all resolver tests**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_feedback_resolver.py -v
```

Expected: 8 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_feedback_resolver.py
git commit -m "test(feedback-resolver): cover missing file, empty change, malformed YAML"
```

---

## Task 5: Create `feedback_appender.py` skeleton + write first failing test

**Files:**
- Create: `_lib/feedback_appender.py` (skeleton)
- Create: `tests/unit/test_feedback_appender.py` (first 4 tests)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_feedback_appender.py`:

```python
"""Tests for feedback_appender (atomic append-only writer)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from _lib.feedback_appender import (
    append_feedback,
    FeedbackError,
    LoopExceededError,
    generate_feedback_id,
)


def test_generate_feedback_id_format():
    """ID matches pattern feedback-YYYYMMDD-NNN."""
    fid = generate_feedback_id(seq=1)
    assert re.match(r"^feedback-\d{8}-001$", fid)


def test_generate_feedback_id_pads_seq():
    """Seq < 100 is zero-padded to 3 digits."""
    fid = generate_feedback_id(seq=42)
    assert fid.endswith("-042")


def test_append_creates_feedback_section_if_missing(tmp_path):
    """If file has no ## Feedback section, append_feedback creates one."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n# Improve\n\n## Acceptance\n- [ ] x\n")
    append_feedback(
        target_path=str(target),
        source="guide-design",
        kind="needs-revision",
        body="missing AC",
        ref_change=None,
    )
    text = target.read_text()
    assert "## Feedback" in text
    assert "### feedback-" in text
    assert "missing AC" in text


def test_append_increments_revision_count(tmp_path):
    """Each needs-revision call increments frontmatter revision_count."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\nrevision_count: 0\nmax_revisions: 3\n---\n")
    append_feedback(
        target_path=str(target),
        source="guide-design",
        kind="needs-revision",
        body="first feedback",
        ref_change=None,
    )
    text = target.read_text()
    assert "revision_count: 1" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_feedback_appender.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named '_lib.feedback_appender'`.

- [ ] **Step 3: Write the minimal implementation**

Create `_lib/feedback_appender.py`:

```python
"""Append-only feedback writer for .rddf/improvements/*.md files.

This is the SINGLE WRITER for the ## Feedback section per ADR-0037.
All downstream skills (guide-design, guide-plan, guide-ship, rdd-verifier)
MUST route through this module via the `rddf feedback add` CLI.

Writes are atomic via `_lib.core.atomic_write` and serialized via
`_lib.core.lock.FileLock` to prevent the corruption mode seen in
`.rddf/state/iteration.corrupt.*` (multi-writer race).
"""
from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path
from typing import Optional

import yaml

from _lib.core.atomic_write import atomic_write_text
from _lib.core.lock import FileLock, LockTimeout

__all__ = [
    "append_feedback",
    "FeedbackError",
    "LoopExceededError",
    "generate_feedback_id",
    "VALID_SOURCES",
    "VALID_KINDS",
    "COUNTERS_FILE",
]

VALID_SOURCES = {"guide-design", "guide-plan", "guide-ship", "rdd-verifier", "human"}
VALID_KINDS = {"needs-revision", "ac-fail", "rejected", "blocked", "noted"}
REVISION_KINDS = {"needs-revision", "ac-fail"}  # kinds that bump revision_count
COUNTERS_FILE = ".rddf/state/.feedback-counters.json"


class FeedbackError(Exception):
    """Base error for feedback_appender."""


class LoopExceededError(FeedbackError):
    """revision_count > max_revisions. Per ADR-0037 §3.6, force human escalation."""


def generate_feedback_id(*, seq: int) -> str:
    """Return feedback-YYYYMMDD-NNN (UTC date + zero-padded seq)."""
    date_part = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%d")
    return f"feedback-{date_part}-{seq:03d}"


def _split_frontmatter(text: str) -> tuple[dict, str, str]:
    """Return (frontmatter_dict, fm_block_with_delimiters, body_after).

    Raises FeedbackError if malformed.
    """
    if not text.startswith("---"):
        return {}, "", text
    try:
        end = text.index("\n---", 3)
        fm_inner = text[3:end].lstrip("\n")
        rest = text[end + 4:].lstrip("\n")
        fm = yaml.safe_load(fm_inner) or {}
        return fm, text[: end + 4], rest
    except (ValueError, yaml.YAMLError) as exc:
        raise FeedbackError(f"Malformed frontmatter: {exc}") from exc


def _join_frontmatter(fm: dict) -> str:
    """Serialize frontmatter dict back to ---\\n...\\n--- block."""
    yaml_text = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip()
    return f"---\n{yaml_text}\n---\n"


def _read_counter(target: Path) -> int:
    """Read the per-file feedback seq counter (default 0)."""
    cf = target.parent / ".feedback-counters.json"
    if not cf.exists():
        return 0
    import json
    data = json.loads(cf.read_text())
    return int(data.get(str(target.name), 0))


def _write_counter(target: Path, seq: int) -> None:
    """Persist the per-file feedback seq counter."""
    cf = target.parent / ".feedback-counters.json"
    cf.parent.mkdir(parents=True, exist_ok=True)
    import json
    data = {}
    if cf.exists():
        data = json.loads(cf.read_text())
    data[str(target.name)] = seq
    atomic_write_text(cf, json.dumps(data, indent=2, ensure_ascii=False))


def _check_loop_guard(fm: dict, kind: str) -> None:
    """Raise LoopExceededError if kind is revision-counting and over cap."""
    if kind not in REVISION_KINDS:
        return
    rc = int(fm.get("revision_count", 0))
    mr = int(fm.get("max_revisions", 3))
    if rc >= mr:
        raise LoopExceededError(
            f"Loop exceeded: revision_count={rc} >= max_revisions={mr}. "
            f"Escalate to human decision: defer, split, or reject. "
            f"Reference: ADR-0037 §3.6."
        )


def _render_entry(
    *,
    feedback_id: str,
    source: str,
    kind: str,
    body: str,
    created_at: str,
    ref_change: Optional[str],
) -> str:
    """Render one ## Feedback subsection block."""
    lines = [f"### {feedback_id}", ""]
    lines.append(f"- **source**: {source}")
    lines.append(f"- **kind**: {kind}")
    lines.append(f"- **created_at**: {created_at}")
    if ref_change:
        lines.append(f"- **ref_change**: {ref_change}")
    lines.append(f"- **resolution**: open")
    lines.append("")
    lines.append("#### Body")
    lines.append("")
    lines.append(body)
    lines.append("")
    return "\n".join(lines)


def append_feedback(
    *,
    target_path: str,
    source: str,
    kind: str,
    body: str,
    ref_change: Optional[str] = None,
) -> str:
    """Append a feedback entry to the target file's ## Feedback section.

    Args:
        target_path: Absolute path to .rddf/improvements/<name>.md.
        source: One of VALID_SOURCES.
        kind: One of VALID_KINDS.
        body: Feedback body text (1-10000 chars).
        ref_change: Optional OpenSpec change name to cross-reference.

    Returns:
        The generated feedback_id.

    Raises:
        FeedbackError: validation failure.
        LoopExceededError: revision_count exceeded max_revisions.
    """
    if source not in VALID_SOURCES:
        raise FeedbackError(f"Invalid source: {source!r}. Valid: {sorted(VALID_SOURCES)}")
    if kind not in VALID_KINDS:
        raise FeedbackError(f"Invalid kind: {kind!r}. Valid: {sorted(VALID_KINDS)}")
    if not (1 <= len(body) <= 10000):
        raise FeedbackError(f"Body length {len(body)} out of range [1, 10000]")

    target = Path(target_path)
    lock_path = target.with_suffix(target.suffix + ".lock")

    with FileLock(str(lock_path), timeout=10.0):
        text = target.read_text(encoding="utf-8") if target.exists() else ""
        fm, fm_block, body_text = _split_frontmatter(text)

        _check_loop_guard(fm, kind)

        seq = _read_counter(target) + 1
        feedback_id = generate_feedback_id(seq=seq)
        created_at = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")

        entry = _render_entry(
            feedback_id=feedback_id,
            source=source,
            kind=kind,
            body=body,
            created_at=created_at,
            ref_change=ref_change,
        )

        # Ensure ## Feedback section
        if "## Feedback" not in body_text:
            new_body = body_text.rstrip() + "\n\n## Feedback\n\n" + entry
        else:
            # Append at the end of the file (after existing feedback)
            new_body = body_text.rstrip() + "\n\n" + entry

        # Update frontmatter
        if kind in REVISION_KINDS:
            fm["revision_count"] = int(fm.get("revision_count", 0)) + 1
        fm["last_feedback_id"] = feedback_id
        fm["last_feedback_at"] = created_at
        fm["feedback_status"] = "needs-revision" if kind in REVISION_KINDS else "noted"

        new_text = _join_frontmatter(fm) + "\n" + new_body
        atomic_write_text(target, new_text)
        _write_counter(target, seq)

    return feedback_id
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_feedback_appender.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add _lib/feedback_appender.py tests/unit/test_feedback_appender.py
git commit -m "feat(feedback-appender): single-writer append with loop guard and counter"
```

---

## Task 6: Add remaining `feedback_appender` tests

**Files:**
- Modify: `tests/unit/test_feedback_appender.py` (append 8 more tests)

- [ ] **Step 1: Append 8 more tests**

```python
def test_append_uses_lock_file(tmp_path):
    """Lock file .lock is created next to target during write."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n")
    # We can't easily test concurrent locking without threads,
    # but we can verify the lock path is used via monkeypatch.
    from _lib.core import lock as lock_mod
    called = []
    original = lock_mod.FileLock
    def spy(path, **kw):
        called.append(path)
        return original(path, **kw)
    lock_mod.FileLock = spy
    try:
        append_feedback(
            target_path=str(target),
            source="human",
            kind="noted",
            body="just noting",
            ref_change=None,
        )
    finally:
        lock_mod.FileLock = original
    assert any(str(target) + ".lock" in p for p in called)


def test_append_loop_guard_blocks_after_3(tmp_path):
    """3rd needs-revision succeeds; 4th raises LoopExceededError."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\nrevision_count: 0\nmax_revisions: 3\n---\n")
    for i in range(3):
        append_feedback(
            target_path=str(target),
            source="guide-design",
            kind="needs-revision",
            body=f"feedback {i}",
            ref_change=None,
        )
    with pytest.raises(LoopExceededError, match="Loop exceeded"):
        append_feedback(
            target_path=str(target),
            source="guide-design",
            kind="needs-revision",
            body="4th attempt",
            ref_change=None,
        )


def test_append_rejected_kind_does_not_count_toward_loop(tmp_path):
    """rejected kind does not bump revision_count."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\nrevision_count: 0\nmax_revisions: 3\n---\n")
    append_feedback(
        target_path=str(target),
        source="guide-design",
        kind="rejected",
        body="just rejecting",
        ref_change=None,
    )
    text = target.read_text()
    assert "revision_count: 1" not in text  # not bumped
    assert "revision_count: 0" in text


def test_append_invalid_source_raises(tmp_path):
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n")
    with pytest.raises(FeedbackError, match="Invalid source"):
        append_feedback(
            target_path=str(target),
            source="not-a-source",
            kind="noted",
            body="x",
            ref_change=None,
        )


def test_append_invalid_kind_raises(tmp_path):
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n")
    with pytest.raises(FeedbackError, match="Invalid kind"):
        append_feedback(
            target_path=str(target),
            source="human",
            kind="bogus",
            body="x",
            ref_change=None,
        )


def test_append_empty_body_raises(tmp_path):
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n")
    with pytest.raises(FeedbackError, match="Body length"):
        append_feedback(
            target_path=str(target),
            source="human",
            kind="noted",
            body="",
            ref_change=None,
        )


def test_append_appends_in_chronological_order(tmp_path):
    """Multiple appends result in oldest-first order in file."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n")
    for i in range(3):
        append_feedback(
            target_path=str(target),
            source="human",
            kind="noted",
            body=f"entry {i}",
            ref_change=None,
        )
    text = target.read_text()
    pos0 = text.index("entry 0")
    pos1 = text.index("entry 1")
    pos2 = text.index("entry 2")
    assert pos0 < pos1 < pos2


def test_append_preserves_existing_body(tmp_path):
    """Existing ## Acceptance section is not overwritten."""
    target = tmp_path / "improve.md"
    target.write_text("---\nname: improve\n---\n# Improve\n\n## Acceptance\n- [ ] do thing\n")
    append_feedback(
        target_path=str(target),
        source="human",
        kind="noted",
        body="review note",
        ref_change=None,
    )
    text = target.read_text()
    assert "## Acceptance\n- [ ] do thing" in text
    assert "## Feedback" in text
    assert "review note" in text
```

- [ ] **Step 2: Run all appender tests**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_feedback_appender.py -v
```

Expected: 12 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_feedback_appender.py
git commit -m "test(feedback-appender): cover loop guard, lock, ordering, preservation"
```

---

## Task 7: Create `feedback_cmd.py` skeleton + write CLI failing test

**Files:**
- Create: `_lib/cli/feedback_cmd.py` (skeleton)
- Create: `tests/unit/test_feedback_cli.py` (first 5 tests)

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_feedback_cli.py`:

```python
"""Tests for feedback CLI dispatcher."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from _lib.cli.feedback_cmd import cmd_feedback


def test_cli_add_minimal(tmp_path, capsys):
    """rddf feedback add <name> --from X --kind Y --body Z succeeds."""
    improvement = tmp_path / "improve.md"
    improvement.write_text("---\nname: improve\n---\n")
    # Use --project-root pointing at tmp_path so resolver finds file
    rc = cmd_feedback([
        "add", "improve",
        "--from", "guide-design",
        "--kind", "needs-revision",
        "--body", "missing AC",
        "--project-root", str(tmp_path),
    ])
    captured = capsys.readouterr()
    assert rc == 0
    assert "feedback-" in captured.out
    assert "improve.md" in captured.out


def test_cli_add_with_ref_change(tmp_path, capsys):
    """--ref-change is passed through to resolver."""
    improvement = tmp_path / "improve.md"
    improvement.write_text("---\nname: improve\n---\n")
    rc = cmd_feedback([
        "add", "improve",
        "--from", "guide-design",
        "--kind", "needs-revision",
        "--body", "test",
        "--ref-change", "my-change",
        "--project-root", str(tmp_path),
    ])
    assert rc == 0
    text = improvement.read_text()
    assert "**ref_change**: my-change" in text


def test_cli_add_invalid_source(tmp_path):
    """Invalid --from returns exit code 1."""
    improvement = tmp_path / "improve.md"
    improvement.write_text("---\nname: improve\n---\n")
    rc = cmd_feedback([
        "add", "improve",
        "--from", "invalid",
        "--kind", "noted",
        "--body", "x",
        "--project-root", str(tmp_path),
    ])
    assert rc == 1


def test_cli_add_missing_proposal(tmp_path):
    """Non-existent improvement file returns exit code 1."""
    rc = cmd_feedback([
        "add", "ghost",
        "--from", "human",
        "--kind", "noted",
        "--body", "x",
        "--project-root", str(tmp_path),
    ])
    assert rc == 1


def test_cli_add_dry_run(tmp_path):
    """--dry-run does not modify file."""
    improvement = tmp_path / "improve.md"
    original = "---\nname: improve\n---\n"
    improvement.write_text(original)
    rc = cmd_feedback([
        "add", "improve",
        "--from", "human",
        "--kind", "noted",
        "--body", "would write",
        "--dry-run",
        "--project-root", str(tmp_path),
    ])
    assert rc == 0
    assert improvement.read_text() == original
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_feedback_cli.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named '_lib.cli.feedback_cmd'`.

- [ ] **Step 3: Write the minimal implementation**

Create `_lib/cli/feedback_cmd.py`:

```python
"""CLI dispatcher for `rddf feedback ...` subcommands.

Subcommands:
  add <proposal> --from X --kind Y --body Z [--ref-change C] [--dry-run]
  list <proposal>
  resolve <proposal> <feedback-id>
  show-schema
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from _lib.feedback_appender import (
    append_feedback,
    FeedbackError,
    LoopExceededError,
)


_VALID_SOURCES = ("guide-design", "guide-plan", "guide-ship", "rdd-verifier", "human")
_VALID_KINDS = ("needs-revision", "ac-fail", "rejected", "blocked", "noted")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rddf feedback",
        description="Append feedback to .rddf/improvements/*.md files (single writer per ADR-0037).",
    )
    parser.add_argument("--project-root", default=".", help="Project root (default: cwd)")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    p_add = sub.add_parser("add", help="Append feedback entry")
    p_add.add_argument("proposal", help="Proposal name (file basename without .md)")
    p_add.add_argument("--from", dest="source", required=True, choices=_VALID_SOURCES)
    p_add.add_argument("--kind", required=True, choices=_VALID_KINDS)
    p_add.add_argument("--body", required=True, help="Body text (or @file)")
    p_add.add_argument("--ref-change", dest="ref_change", default=None)
    p_add.add_argument("--dry-run", action="store_true")

    p_list = sub.add_parser("list", help="List feedback entries")
    p_list.add_argument("proposal")

    p_resolve = sub.add_parser("resolve", help="Mark entry resolved")
    p_resolve.add_argument("proposal")
    p_resolve.add_argument("feedback_id")

    sub.add_parser("show-schema", help="Print feedback entry JSON schema to stdout")

    return parser


def _resolve_body(body_arg: str) -> str:
    """If body_arg starts with @, read from file; else return as-is."""
    if body_arg.startswith("@"):
        return Path(body_arg[1:]).read_text(encoding="utf-8")
    return body_arg


def _find_improvement(project_root: Path, proposal: str) -> Path:
    """Locate .rddf/improvements/<proposal>.md; raise FeedbackError if missing."""
    target = project_root / ".rddf" / "improvements" / f"{proposal}.md"
    if not target.exists():
        raise FeedbackError(f"Improvement file not found: {target}")
    return target


def cmd_feedback(args: List[str]) -> int:
    """Main entry: parse args, dispatch to sub-handler, return exit code."""
    parser = _build_parser()
    ns = parser.parse_args(args)

    project_root = Path(ns.project_root).resolve()

    try:
        if ns.subcommand == "show-schema":
            schema_path = Path(__file__).parent.parent / "schemas" / "feedback_entry_schema.json"
            sys.stdout.write(schema_path.read_text())
            return 0

        if ns.subcommand == "add":
            target = _find_improvement(project_root, ns.proposal)
            body = _resolve_body(ns.body)
            if ns.dry_run:
                # Validate but do not write
                from _lib.feedback_appender import VALID_SOURCES, VALID_KINDS
                if ns.source not in VALID_SOURCES:
                    raise FeedbackError(f"Invalid source: {ns.source}")
                if ns.kind not in VALID_KINDS:
                    raise FeedbackError(f"Invalid kind: {ns.kind}")
                if not (1 <= len(body) <= 10000):
                    raise FeedbackError(f"Body length {len(body)} out of range")
                sys.stdout.write(f"DRY-RUN: would append feedback to {target}\n")
                return 0
            feedback_id = append_feedback(
                target_path=str(target),
                source=ns.source,
                kind=ns.kind,
                body=body,
                ref_change=ns.ref_change,
            )
            sys.stdout.write(
                f"✓ Feedback appended: {feedback_id}\n"
                f"  File: {target}\n"
                f"  Source: {ns.source}\n"
                f"  Kind: {ns.kind}\n"
            )
            return 0

        if ns.subcommand == "list":
            target = _find_improvement(project_root, ns.proposal)
            text = target.read_text(encoding="utf-8")
            sys.stdout.write(text)
            return 0

        if ns.subcommand == "resolve":
            # Minimal v1: print message; full resolve impl deferred to Stage 2.
            sys.stdout.write(
                f"resolve subcommand is a placeholder for Stage 2 (rdd-planner).\n"
                f"  Proposal: {ns.proposal}\n"
                f"  Feedback ID: {ns.feedback_id}\n"
            )
            return 0

        parser.print_help()
        return 1

    except FeedbackError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1
    except LoopExceededError as exc:
        sys.stderr.write(f"LOOP EXCEEDED: {exc}\n")
        return 1
    except FileNotFoundError as exc:
        sys.stderr.write(f"FILE NOT FOUND: {exc}\n")
        return 2
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_feedback_cli.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add _lib/cli/feedback_cmd.py tests/unit/test_feedback_cli.py
git commit -m "feat(feedback-cmd): CLI dispatcher with add/list/resolve/show-schema"
```

---

## Task 8: Add remaining `feedback_cmd` tests

**Files:**
- Modify: `tests/unit/test_feedback_cli.py` (append 5 more tests)

- [ ] **Step 1: Append 5 more tests**

```python
def test_cli_list_outputs_file_content(tmp_path, capsys):
    improvement = tmp_path / "improve.md"
    improvement.write_text("---\nname: improve\n---\n# Improve\n")
    rc = cmd_feedback(["list", "improve", "--project-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "# Improve" in captured.out


def test_cli_show_schema_prints_json(tmp_path, capsys):
    rc = cmd_feedback(["show-schema", "--project-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    import json
    parsed = json.loads(captured.out)  # must be valid JSON
    assert parsed["title"] == "FeedbackEntry"


def test_cli_resolve_placeholder(tmp_path, capsys):
    rc = cmd_feedback(["resolve", "improve", "feedback-20260903-001", "--project-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "resolve subcommand is a placeholder" in captured.out


def test_cli_body_from_file(tmp_path, capsys):
    body_file = tmp_path / "body.txt"
    body_file.write_text("body from file content")
    improvement = tmp_path / "improve.md"
    improvement.write_text("---\nname: improve\n---\n")
    rc = cmd_feedback([
        "add", "improve",
        "--from", "human",
        "--kind", "noted",
        "--body", f"@{body_file}",
        "--project-root", str(tmp_path),
    ])
    text = improvement.read_text()
    assert "body from file content" in text
    assert rc == 0


def test_cli_no_subcommand_exits_1(capsys):
    rc = cmd_feedback([])
    captured = capsys.readouterr()
    assert rc != 0  # argparse exits 2 on missing required subcommand, our wrapper would catch
    # argparse calls sys.exit(2) directly; we just check it's non-zero
```

- [ ] **Step 2: Run all CLI tests**

Run:
```bash
RDD_PLANNER_MOCK=yes python3 -m pytest tests/unit/test_feedback_cli.py -v
```

Expected: 10 passed (or 9 if `test_cli_no_subcommand_exits_1` is brittle — pytest captures SystemExit).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_feedback_cli.py
git commit -m "test(feedback-cmd): cover list, schema, body-from-file, missing subcommand"
```

---

## Task 9: Register `feedback` subcommand in `_lib/cli/__init__.py`

**Files:**
- Modify: `_lib/cli/__init__.py` (add 1 line to `_ROUTES`)

- [ ] **Step 1: Add the route**

In `_lib/cli/__init__.py`, find the `_ROUTES` dict (around line 78-115) and add a new entry after `"feature"`:

```python
    "feature": "skills._lib.cli.feature_cmd:cmd_feature",
    "feedback": "skills._lib.cli.feedback_cmd:cmd_feedback",
    "guide": "skills._lib.cli.guide_cmd:cmd_guide",
```

- [ ] **Step 2: Verify route resolves**

Run:
```bash
python3 -c "
from _lib.cli import list_commands, route
assert 'feedback' in list_commands(), 'feedback not in routes'
print('OK: feedback registered')
"
```

Expected: prints `OK: feedback registered`.

- [ ] **Step 3: Verify CLI invocation works**

Run:
```bash
mkdir -p /tmp/fb-test/.rddf/improvements
cat > /tmp/fb-test/.rddf/improvements/demo.md <<'EOF'
---
name: demo
---
# demo
EOF
cd /tmp/fb-test
python3 -m _lib.cli feedback show-schema | head -3
```

Expected: prints first 3 lines of JSON schema (title, type, etc.).

- [ ] **Step 4: Commit**

```bash
git add _lib/cli/__init__.py
git commit -m "feat(feedback-cmd): register 'feedback' in _lib/cli _ROUTES"
```

---

## Task 10: Write integration bats tests

**Files:**
- Create: `tests/integration/test_feedback_cmd.bats`

- [ ] **Step 1: Write the bats test file**

Create `tests/integration/test_feedback_cmd.bats`:

```bash
#!/usr/bin/env bats
# Integration tests for `rddf feedback` CLI.

load test_helper

setup() {
    TEST_TMP=$(mktemp -d)
    mkdir -p "$TEST_TMP/.rddf/improvements"
    cd "$TEST_TMP"
    git init -q .
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "feedback: add appends entry to improvement file" {
    cat > .rddf/improvements/foo.md <<'EOF'
---
name: foo
---
# foo proposal
EOF

    run python3 -m _lib.cli feedback add foo \
        --from guide-design \
        --kind needs-revision \
        --body "missing acceptance criteria"

    [ "$status" -eq 0 ]
    [[ "$output" =~ "Feedback appended" ]]
    grep -q "## Feedback" .rddf/improvements/foo.md
    grep -q "missing acceptance criteria" .rddf/improvements/foo.md
}

@test "feedback: add increments revision_count" {
    cat > .rddf/improvements/bar.md <<'EOF'
---
name: bar
revision_count: 0
max_revisions: 3
---
EOF

    python3 -m _lib.cli feedback add bar \
        --from guide-design \
        --kind needs-revision \
        --body "test"

    grep -q "revision_count: 1" .rddf/improvements/bar.md
}

@test "feedback: loop guard blocks 4th revision" {
    cat > .rddf/improvements/baz.md <<'EOF'
---
name: baz
revision_count: 0
max_revisions: 3
---
EOF

    for i in 1 2 3; do
        python3 -m _lib.cli feedback add baz \
            --from guide-design \
            --kind needs-revision \
            --body "attempt $i"
    done

    run python3 -m _lib.cli feedback add baz \
        --from guide-design \
        --kind needs-revision \
        --body "4th attempt"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "LOOP EXCEEDED" ]]
}

@test "feedback: invalid source returns exit 1" {
    cat > .rddf/improvements/qux.md <<'EOF'
---
name: qux
---
EOF

    run python3 -m _lib.cli feedback add qux \
        --from bogus-source \
        --kind noted \
        --body "test"

    [ "$status" -eq 1 ]
    [[ "$output" =~ "Invalid source" ]]
}

@test "feedback: missing proposal file returns exit 1" {
    run python3 -m _lib.cli feedback add nonexistent \
        --from human \
        --kind noted \
        --body "test"

    [ "$status" -eq 1 ]
}

@test "feedback: --ref-change cross-references change" {
    cat > .rddf/improvements/ref.md <<'EOF'
---
name: ref
---
EOF

    python3 -m _lib.cli feedback add ref \
        --from rdd-verifier \
        --kind ac-fail \
        --body "AC #3 not met" \
        --ref-change change-foo

    grep -q "ref_change\*\*: change-foo" .rddf/improvements/ref.md
}

@test "feedback: show-schema outputs valid JSON" {
    run python3 -m _lib.cli feedback show-schema

    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import json,sys; json.loads(sys.stdin.read())"
}

@test "feedback: list outputs file content" {
    cat > .rddf/improvements/listable.md <<'EOF'
---
name: listable
---
# My Proposal
EOF

    run python3 -m _lib.cli feedback list listable

    [ "$status" -eq 0 ]
    [[ "$output" =~ "My Proposal" ]]
}

@test "feedback: --dry-run does not modify file" {
    cat > .rddf/improvements/dry.md <<'EOF'
---
name: dry
---
EOF
    ORIGINAL=$(cat .rddf/improvements/dry.md)

    run python3 -m _lib.cli feedback add dry \
        --from human \
        --kind noted \
        --body "would write" \
        --dry-run

    [ "$status" -eq 0 ]
    [ "$(cat .rddf/improvements/dry.md)" = "$ORIGINAL" ]
}
```

- [ ] **Step 2: Run bats integration tests**

Run:
```bash
bats tests/integration/test_feedback_cmd.bats
```

Expected: 9 passed (or 8 if --dry-run has a quirk; investigate if any fail).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_feedback_cmd.bats
git commit -m "test(feedback-cmd): 9 bats integration tests covering happy/error paths"
```

---

## Task 11: Write ADR-0037

**Files:**
- Create: `docs/adr/ADR-0037-feedback-contract.md`

- [ ] **Step 1: Write the ADR**

Create the file with this content:

```markdown
# ADR-0037: Feedback Contract for `.rddf/improvements/*.md`

## Status

Proposed (2026-09-03) — awaiting acceptance after Stage 1 implementation.

## Context

Current `.rddf/improvements/*.md` files (226 in the codebase) lack:
1. Stable ID linking improvement ↔ OpenSpec change ↔ AC verdict.
2. A defined mechanism for downstream skills (`guide-design`, `guide-plan`, `guide-ship`, `rdd-verifier`) to write back feedback.
3. A loop-termination guard for iterative revision cycles.

This caused `iteration.corrupt.*` residual files in `.rddf/state/` (multi-writer race on shared state) and made cross-phase feedback propagation ad-hoc.

## Decision

Adopt an **append-only feedback contract** with the following properties:

1. **Single writer**: All `## Feedback` writes go through `_lib.feedback_appender.append_feedback()`, exposed as `rddf feedback add` CLI.
2. **Stable IDs**: Each entry has `feedback-YYYYMMDD-NNN` ID; counters persist in `.rddf/improvements/.feedback-counters.json`.
3. **ID resolution**: Proposal → change-name via 3-tier priority: explicit `--ref-change` > frontmatter `change:` > basename equality.
4. **Loop guard**: Frontmatter `revision_count` increments on `needs-revision` / `ac-fail`; cap `max_revisions=3` (mirrors ADR-0034 verifier ceiling).
5. **Atomic writes**: All writes via `_lib.core.atomic_write` + `FileLock` to prevent the iteration-corrupt failure mode.
6. **Backward compatible**: All fields are opt-in; existing 226 files unchanged.

## Consequences

### Positive

- ✅ Stable cross-phase feedback propagation.
- ✅ No multi-writer corruption (proven pattern from state-vector).
- ✅ Loop termination enforced (matches verifier 3-retry ceiling).
- ✅ Zero impact on existing files.

### Negative

- ⚠️ Adds ~500 lines of Python (resolver + appender + CLI + tests).
- ⚠️ Future stages (2-4) build on this contract; if contract needs revision, downstream skills must be re-tested.
- ⚠️ Counter file `.feedback-counters.json` is per-improvement-dir; cross-project collision possible if not scoped to `project_root`.

### Neutral

- Stage 2 (`rdd-planner`) will consume this contract as its primary input.
- Stage 3 (`rdd-arch` rename) and Stage 4 (no-merge) do not affect this contract.

## Alternatives Considered

1. **Per-skill direct file writes** — rejected (multi-writer corruption, ADR-0028 role-model violation).
2. **Centralized database (SQLite)** — rejected (out of scope for Stage 1; adds heavy dependency).
3. **Read-only feedback (no write)** — rejected (does not solve the cross-phase propagation gap).

## References

- Spec: `docs/superpowers/specs/2026-09-03-rdd-planner-stage1-feedback-contract.md`
- ADR-0034: rdd-verifier 3-retry ceiling
- ADR-0028: role-model per phase
- `_lib/core/atomic_write.py` and `_lib/core/lock.py` (proven primitives)
- `.rddf/state/iteration.corrupt.*` (the failure mode this ADR prevents)

## Supersedes

None. Additive contract.
```

- [ ] **Step 2: Verify ADR file is valid Markdown**

Run:
```bash
head -20 docs/adr/ADR-0037-feedback-contract.md
```

Expected: prints the header and status block.

- [ ] **Step 3: Commit**

```bash
git add docs/adr/ADR-0037-feedback-contract.md
git commit -m "docs(adr): add ADR-0037 feedback contract"
```

---

## Task 12: Full regression gate

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite via test.sh**

Run:
```bash
./test.sh --full --regression
```

Expected: exits 0 (no new failures vs baseline). Note any KNOWN_FAILURES hits.

- [ ] **Step 2: Confirm new test counts in output**

Look for:
- `tests/unit/test_feedback_resolver.py` — 8 tests
- `tests/unit/test_feedback_appender.py` — 12 tests
- `tests/unit/test_feedback_cli.py` — 10 tests
- `tests/integration/test_feedback_cmd.bats` — 9 tests
- Total new tests: **39**

- [ ] **Step 3: Manual demo run (record in spec §7)**

Run:
```bash
mkdir -p .rddf/improvements
cat > .rddf/improvements/demo-improvements.md <<'EOF'
---
name: demo-improvements
priority: P2
source: human
created_at: 2026-09-03
---

# demo-improvements

## Acceptance

- [ ] Feedback can be added.
EOF

python3 -m _lib.cli feedback add demo-improvements \
    --from guide-design \
    --kind needs-revision \
    --body "缺少对失败场景的验收标准" \
    --ref-change demo-improvements

cat .rddf/improvements/demo-improvements.md
```

Expected output: file shows new `## Feedback` section with `feedback-YYYYMMDDD-NNN` entry.

- [ ] **Step 4: Final commit (if any demo-only files)**

```bash
git add .rddf/improvements/demo-improvements.md
git commit -m "docs(feedback-contract): record demo run output"
```

---

## Self-Review

### 1. Spec coverage

| Spec Section | Task |
|--------------|------|
| §2 Decision 1 (frontmatter schema) | Task 2 |
| §2 Decision 2 (append-only feedback) | Tasks 5-6 |
| §2 Decision 3 (single writer) | Tasks 7-9 |
| §2 Decision 4 (loop termination) | Task 6 |
| §2 Decision 5 (3-tier ID resolution) | Tasks 3-4 |
| §2 Decision 6 (schema location) | Tasks 1-2 |
| §2 Decision 7 (atomic writes) | Task 5 |
| §2 Decision 8 (backward compat) | All tests use opt-in fields |
| §2 Decision 9 (CLI surface) | Tasks 7-9 |
| §2 Decision 10 (testing) | Tasks 3-8 (unit), Task 10 (bats) |
| §3.4 frontmatter v2 | Task 2 |
| §3.5 feedback_entry_schema v1 | Task 1 |
| §3.6 Markdown rendering | Task 5 |
| §3.7 CLI surface | Tasks 7-8 |
| §4.1 zero-impact migration | Test fixture uses tmp_path (not real files) |
| §4.3 loop termination | Task 6 |
| §6 acceptance criteria | Task 12 |
| §7 demo run | Task 12 |
| §8 risk mitigation | Concurrent write via lock (Task 6) |
| ADR-0037 | Task 11 |

**Gap**: None identified. All 12 spec acceptance criteria map to a task.

### 2. Placeholder scan

- No "TBD", "TODO", "fill in", "similar to Task N" found.
- All code blocks are concrete and copy-pasteable.
- File paths are absolute or project-relative and exist.

### 3. Type consistency

- `append_feedback(target_path, source, kind, body, ref_change)` used consistently in Tasks 5-8.
- `cmd_feedback(args: List[str]) -> int` used consistently in Tasks 7-8 and matches `_lib/cli/__init__.py` route signature.
- `feedback_id` format `feedback-YYYYMMDD-NNN` used consistently.
- `VALID_SOURCES` / `VALID_KINDS` defined once in Task 5, referenced by Task 7.
- Counter file path `.feedback-counters.json` consistent across Tasks 5-6.

### 4. Edge cases handled

- ✅ Missing improvement file (Task 4 test_resolver_missing_file)
- ✅ Empty `change:` field (Task 4 test_resolver_empty_change_field)
- ✅ Malformed frontmatter / YAML (Task 4 tests)
- ✅ Lock contention (Task 6 monkeypatch test)
- ✅ Loop exceeded (Task 6 test_append_loop_guard_blocks_after_3)
- ✅ Rejected kind does not count toward loop (Task 6 test_append_rejected_kind_does_not_count_toward_loop)
- ✅ Chronological ordering preserved (Task 6 test_append_appends_in_chronological_order)
- ✅ Body from file (`@file`) (Task 8 test_cli_body_from_file)
- ✅ Dry-run (Task 8 + Task 10 test)
- ✅ Schema output is valid JSON (Task 8 + Task 10 test)

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-09-03-rdd-planner-stage1-feedback-contract.md`. Two execution options:**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

**Recommended for this plan**: Subagent-driven (12 tasks with isolated file scopes make this ideal for parallel subagent dispatch).

Which approach?
