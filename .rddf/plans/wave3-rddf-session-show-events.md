# wave3-rddf-session-show-events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 添加 `rddf session show --events` CLI 子命令，支持按 owner/session/kind/time-range 过滤 events.jsonl 历史回放，解决当前 events.jsonl 只写不读的问题。

**Architecture:** 新增 `_lib/cli/session_show_cmd.py` 实现 argparse 子命令解析 + 过滤组合 + 格式渲染；在 `_lib/cli/sessions_cmd.py` 注册为 `show` 的子命令。

**Tech Stack:** Python (argparse, json, datetime)

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `_lib/cli/session_show_cmd.py` (NEW) | `rddf session show --events` 子命令: 6 个 flag + 过滤 + 3 种输出格式 |
| `_lib/cli/sessions_cmd.py` | 注册 `show --events` 子命令分派 |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_session_show_events.py` (NEW) | 过滤组合 × 格式变体 × 空 events case |

---

### Task 1: Implement core CLI subcommand — filter + format logic

**Files:**
- Create: `_lib/cli/session_show_cmd.py` (~80 LOC)
- Modify: `_lib/cli/sessions_cmd.py`
- Test: `tests/unit/test_session_show_events.py`

- [x] **Step 1: Write failing test for session_show_cmd filter logic**

Create `tests/unit/test_session_show_events.py`:

```python
"""Unit tests for session_show_cmd: filter combinators + format variants."""
import json
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "_lib"))

from cli.session_show_cmd import build_event_query, format_events_table, format_events_json, format_events_raw

SAMPLE_EVENTS = [
    {"event_id": "evt_001", "ts": "2026-09-24T01:00:00Z", "event_type": "phase_started",
     "kind": "stage_builder", "owner_opencode_session_id": "owner_a",
     "session_id": "rds_001", "message": "started", "context": {}},
    {"event_id": "evt_002", "ts": "2026-09-24T01:05:00Z", "event_type": "phase_completed",
     "kind": "stage_builder", "owner_opencode_session_id": "owner_a",
     "session_id": "rds_001", "message": "completed", "context": {}},
    {"event_id": "evt_003", "ts": "2026-09-24T02:00:00Z", "event_type": "phase_started",
     "kind": "stage_guide", "owner_opencode_session_id": "owner_b",
     "session_id": "rds_002", "message": "guide started", "context": {}},
]


def test_filter_by_owner():
    """AC-P2-4-1: --owner <owner> filters events."""
    query = build_event_query(owner="owner_a")
    filtered = [e for e in SAMPLE_EVENTS if query(e)]
    assert len(filtered) == 2
    assert all(e["owner_opencode_session_id"] == "owner_a" for e in filtered)


def test_filter_by_session():
    """AC-P2-4-2: --session <sid> filters events."""
    query = build_event_query(session_id="rds_002")
    filtered = [e for e in SAMPLE_EVENTS if query(e)]
    assert len(filtered) == 1
    assert filtered[0]["session_id"] == "rds_002"


def test_filter_by_kind():
    """AC-P2-4-3: --kind <kind> filters events."""
    query = build_event_query(kind="stage_guide")
    filtered = [e for e in SAMPLE_EVENTS if query(e)]
    assert len(filtered) == 1
    assert filtered[0]["kind"] == "stage_guide"


def test_filter_combined():
    """AC-P2-4-4 implied: AND filter combinators."""
    query = build_event_query(owner="owner_a", kind="stage_builder")
    filtered = [e for e in SAMPLE_EVENTS if query(e)]
    assert len(filtered) == 2


def test_filter_since_until():
    """AC-P2-4-4: --since/--until ISO 8601 time range."""
    query = build_event_query(since="2026-09-24T01:05:00", until="2026-09-24T01:10:00")
    filtered = [e for e in SAMPLE_EVENTS if query(e)]
    assert len(filtered) == 1
    assert filtered[0]["event_id"] == "evt_002"


def test_format_table():
    """AC-P2-4-5: table format sorted by ts ascending."""
    result = format_events_table(SAMPLE_EVENTS)
    # Should have header + separator + 3 rows
    lines = result.strip().split("\n")
    assert "TIME" in lines[0]
    assert lines[-1].endswith("guide started")  # latest event at bottom


def test_format_json():
    """AC-P2-4-5 implied: JSON output is parseable array."""
    result = format_events_json(SAMPLE_EVENTS)
    parsed = json.loads(result)
    assert isinstance(parsed, list)
    assert len(parsed) == 3


def test_format_raw():
    """AC-P2-4-5 implied: raw output = one JSONL per line."""
    result = format_events_raw(SAMPLE_EVENTS)
    lines = result.strip().split("\n")
    assert len(lines) == 3
    for line in lines:
        parsed = json.loads(line)
        assert "event_id" in parsed


def test_empty_events():
    """AC-P2-4-6: No events => '(no events)'."""
    result_table = format_events_table([])
    assert "(no events)" in result_table
    result_json = format_events_json([])
    assert result_json == "[]"
    result_raw = format_events_raw([])
    assert result_raw.strip() == ""
```

- [x] **Step 2: Run test to verify it fails (module not found)**

Run: `python3 -m pytest tests/unit/test_session_show_events.py -x --tb=long`
Expected: FAIL — `ModuleNotFoundError: No module named 'cli.session_show_cmd'` (classic TDD red)

- [x] **Step 3: Implement session_show_cmd.py**

Create `_lib/cli/session_show_cmd.py` with ~80 lines:

```python
"""rddf session show --events CLI subcommand.

Provides filter combinators + 3 output formats for events.jsonl history replay.
"""
import json
from datetime import datetime, timezone
from typing import Any, Callable, Optional


def build_event_query(
    owner: Optional[str] = None,
    session_id: Optional[str] = None,
    kind: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> Callable[[dict], bool]:
    """Build a filter function from CLI flags (AND composable)."""
    def query(event: dict) -> bool:
        ctx = event.get("context") or {}
        if owner and event.get("owner_opencode_session_id") != owner:
            return False
        if session_id and ctx.get("session_id") != session_id:
            return False
        if kind and event.get("kind") != kind:
            return False
        if since:
            try:
                if event.get("ts", "") < since:
                    return False
            except (ValueError, TypeError):
                pass
        if until:
            try:
                if event.get("ts", "") > until:
                    return False
            except (ValueError, TypeError):
                pass
        return True
    return query


def format_events_table(events: list[dict]) -> str:
    """Default table format: HEADER + separator + rows, sorted by ts ascending."""
    if not events:
        return "(no events)"
    sorted_events = sorted(events, key=lambda e: e.get("ts", ""))
    lines = [
        f"{'TIME':<26} {'KIND':<20} {'SESSION_ID':<20} {'EVENT_TYPE':<20} MESSAGE",
        f"{'----':<26} {'----':<20} {'----------':<20} {'----------':<20} -------",
    ]
    for e in sorted_events:
        ts = (e.get("ts") or "?")[:19]
        kind = (e.get("kind") or "?")[:20]
        sid = ((e.get("context") or {}).get("session_id") or "?")[:20]
        etype = (e.get("event_type") or "?")[:20]
        msg = (e.get("message") or "")[:60]
        lines.append(f"{ts:<26} {kind:<20} {sid:<20} {etype:<20} {msg}")
    return "\n".join(lines) + "\n"


def format_events_json(events: list[dict]) -> str:
    """JSON array output, parseable by jq."""
    return json.dumps(events, ensure_ascii=False, indent=2)


def format_events_raw(events: list[dict]) -> str:
    """One JSONL per line, pipeable to jq."""
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in events)
```

Then register in `_lib/cli/sessions_cmd.py`. The registration pattern (based on existing code):

```python
# In sessions_cmd.py, add import and subcommand registration:
from _lib.cli.session_show_cmd import build_event_query, format_events_table, format_events_json, format_events_raw

def register_show_events(subparsers):
    """Register 'show --events' subcommand."""
    parser = subparsers.add_parser("show", help="Show session details")
    parser.add_argument("--events", action="store_true", help="Show events history")
    parser.add_argument("--owner", help="Filter by owner session ID")
    parser.add_argument("--session", help="Filter by session ID")
    parser.add_argument("--kind", help="Filter by kind (stage_builder, stage_guide, etc.)")
    parser.add_argument("--since", help="ISO 8601 start time (e.g. 2026-09-24T01:00:00)")
    parser.add_argument("--until", help="ISO 8601 end time")
    parser.add_argument("--format", choices=["table", "json", "raw"], default="table")
    parser.add_argument("--include-archive", action="store_true", help="Include archive files")
    parser.set_defaults(func=handle_show_events)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_session_show_events.py -x --tb=short`
Expected: PASS (all 9 tests)

- [x] **Step 5: Defer commit**

---

### Task 2: Wire up sessions_cmd.py + handle empty events path

**Files:**
- Modify: `_lib/cli/sessions_cmd.py`
- Test: `tests/unit/test_session_show_events.py`

- [x] **Step 1: Write test for empty events file**

Add to `test_session_show_events.py`:

```python
def test_handle_no_events_file(capsys, tmp_path):
    """AC-P2-4-6: events.jsonl not found => '(no events)' output."""
    from cli.session_show_cmd import handle_show_events_cmd
    exit_code = handle_show_events_cmd(events_path=str(tmp_path / "nonexistent.jsonl"))
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "no events" in captured.out.lower()
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_session_show_events.py::test_handle_no_events_file -xvs`
Expected: FAIL — `handle_show_events_cmd` not yet wired

- [x] **Step 3: Implement events file reader and registration**

Create `handle_show_events_cmd` function:

```python
def handle_show_events_cmd(
    events_path: str = ".rddf/state/events.jsonl",
    owner: Optional[str] = None,
    session_id: Optional[str] = None,
    kind: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    format: str = "table",
    include_archive: bool = False,
) -> int:
    """Handler for 'rddf session show --events'. Reads events.jsonl, filters, formats."""
    from pathlib import Path
    import sys
    
    events_file = Path(events_path)
    if not events_file.exists():
        # AC-P2-4-6: graceful empty
        if format == "json":
            print("[]")
        elif format == "raw":
            pass  # nothing to print
        else:
            print("(no events)")
        return 0
    
    events = []
    with open(events_file) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    query = build_event_query(owner=owner, session_id=session_id, kind=kind, since=since, until=until)
    filtered = [e for e in events if query(e)]
    
    if format == "json":
        sys.stdout.write(format_events_json(filtered))
    elif format == "raw":
        sys.stdout.write(format_events_raw(filtered))
    else:
        sys.stdout.write(format_events_table(filtered))
    
    return 0
```

Wire in `_lib/cli/sessions_cmd.py`:

```python
# In the show subcommand handler
if args.events:
    from _lib.cli.session_show_cmd import handle_show_events_cmd
    return handle_show_events_cmd(
        events_path=".rddf/state/events.jsonl",
        owner=args.owner,
        session_id=args.session,
        kind=args.kind,
        since=args.since,
        until=args.until,
        format=args.format,
        include_archive=args.include_archive,
    )
```

- [x] **Step 4: Run all tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_session_show_events.py -x --tb=short`
Expected: PASS (10 tests)

- [x] **Step 5: Defer commit**

---

### Task 3: Verify with existing rdd-doctor smoke test

**Files:**
- Existing test infra: `tests/unit/test_rddf_session.py`

- [x] **Step 1: Run existing rdd-doctor session tests to confirm no regression**

Run: `python3 -m pytest tests/unit/test_rddf_session.py -x --tb=short -q`
Expected: PASS (all ~25 tests)

- [x] **Step 2: Verify `rddf session show --events --help` works**

Run: `python3 -m _lib.cli.rddf session show --events --help 2>&1 | head -5`
Expected: Shows arg help

- [x] **Step 3: Manual smoke — run against empty events.jsonl**

```bash
rddf session show --events
# Expected: "(no events)"
```

- [x] **Step 4-5: Final pass + defer commit**

Run: `python3 -m pytest tests/unit/test_session_show_events.py tests/unit/test_rddf_session.py -x --tb=short -q`
Expected: All pass