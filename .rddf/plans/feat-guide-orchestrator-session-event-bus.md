# feat-guide-orchestrator-session-event-bus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `skill_use("execute")` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable `guide` to act as a long-lived "main session entry" that observes rddf-session progress across multiple OpenCode processes via a new events.jsonl file event bus.

**Architecture:**
- Add `stage_guide` as 5th rddf-session kind (schema v2 → v3)
- New `.rddf/state/events.jsonl` file event bus (NOT reuse existing event-log.jsonl — Metis B4 confirmed it doesn't exist)
- Bidirectional stage-level singleton exemption for `stage_guide` (Oracle B1 fix)
- Per-owner `goal.last_seen_offset` in sessions.json (NO seen_by in events, prevents array inflation)
- Owner-scoped parent lookup (replaces `list_sessions()[0]` newest-of-kind)
- `check_heartbeat_timeouts(readonly=True)` readonly variant (scan-state.sh uses)
- `HEARTBEAT_TIMEOUT_BY_KIND` dict (8h for guide, 30min for stages)
- 4 PRs × TDD 5-step discipline
- Worktree mode (existing `.rddf/wt/test-change` is busy)

**Tech Stack:** Python 3.11+, bash, fcntl.flock, pytest, bats, openspec CLI v1.3.1+

---

## File Structure

### Production Code (new)

| File | Responsibility |
|---|---|
| `skills/rddf-session/scripts/events_log.py` | events.jsonl append/read_since/mark_seen/archive_events; fcntl.flock + atomic write + 50MB cap enforcement |

### Production Code (modified)

| File | Responsibility |
|---|---|
| `_lib/schemas/sessions_schema.json` | v2 → v3 (add `stage_guide` to kind enum, `guide-orchestrator` to intent enum, `goal.last_seen_offset` field) |
| `skills/rddf-session/scripts/rddf_session_pkg/_types.py` | Dual add `_VALID_KINDS` (stage_guide + guide-orchestrator); add `HEARTBEAT_TIMEOUT_BY_KIND`; ensure `_KIND_ALIAS["guide-orchestrator"] = "stage_guide"` |
| `skills/rddf-session/scripts/rddf_session_pkg/_commands.py` | Bidirectional singleton exemption (Oracle B1); `list_sessions` accept `owner_opencode_session_id`+`state`; `check_heartbeat_timeouts(readonly=False)` readonly variant |
| `skills/rddf-session/scripts/rddf_session_hooks.sh` | Extend `parent_kind_map` (`stage_arch → stage_guide`); owner-scoped parent lookup; write events; new `rddf_session_hook_guide_entry`/`close`; fix pre-existing detach bug (line 524) |
| `skills/guide/scripts/guide_entry.sh` | Create stage_guide session on launch; polling contract; close on exit |
| `skills/guide/scripts/scan-state.sh` | REMOVE `check_heartbeat_timeouts` call at line 535 (read-only contract) |
| `_lib/cli/monitor_cmd.py` | Dual-path fallback (events.jsonl first, then event-log.jsonl); `.get()` for new event fields |
| `skills/rdd-doctor/scripts/checks/state_schema_check.py` | Add events.jsonl to `_STATE_FILES`; add 2 new assertions |
| `docs/architecture/multi-session.md` | New "Cross-Container Event Bus" section |
| `CHANGELOG.md`, `USAGE.md`, `AGENTS.md` | Sync rddf-session kind list + guide multi-window usage |

### Tests (new)

| File | Responsibility |
|---|---|
| `tests/unit/test_sessions_schema_v3.py` | Schema v3 validation; stage_guide kind accepted; guide-orchestrator kind accepted (Oracle B2 + Metis B5); dual _VALID_KINDS; bidirectional singleton exemption (Oracle B1); 8h timeout |
| `tests/unit/test_events_log.py` | append_event, read_since, archive_events, no_event_log_jsonl_alias (anti-pattern guard), 50MB cap enforced |
| `tests/integration/test_parent_kind_map.bats` | Owner-scoped parent lookup; stage_arch parent null when no guide; stage_design chains through arch |
| `tests/integration/test_rddf_stage_event.bats` | Hook entry writes phase_started; close writes phase_completed/failed |
| `tests/integration/test_monitor_cmd_extended_events.bats` | Monitor reads extended events; fallback to event-log.jsonl |
| `tests/integration/test_guide_cross_container.bats` | Guide creates stage_guide session; two-owner simulation; no-children skips read; renders since last_seen_offset; updates after render; scan-state no longer mutates |
| `tests/integration/test_doctor_state_json.bats` | events.jsonl JSON valid; size within cap; last_seen_offset references legal |

---

## PR 1: schema + types + events 模块（Step 1 of 4）

### Task 1.1: Write failing tests
- [ ] **Step 1**: Write failing test in `tests/unit/test_sessions_schema_v3.py`:

```python
"""Tests for sessions.json schema v3 — stage_guide kind + goal.last_seen_offset."""
import json
import pytest
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
from skills.rddf_session.scripts.rddf_session_pkg._types import _VALID_KINDS, _KIND_ALIAS


def test_stage_guide_kind_accepted(tmp_path):
    """stage_guide in _VALID_KINDS (Oracle B2)."""
    assert "stage_guide" in _VALID_KINDS


def test_guide_orchestrator_kind_accepted_in_valid_kinds():
    """guide-orchestrator in _VALID_KINDS (Oracle B2: belt-and-suspenders pattern)."""
    assert "guide-orchestrator" in _VALID_KINDS


def test_kind_alias_normalizes_guide_orchestrator():
    """_KIND_ALIAS['guide-orchestrator'] == 'stage_guide' (Metis B5)."""
    assert _KIND_ALIAS.get("guide-orchestrator") == "stage_guide"


def test_stage_guide_create_session_succeeds(tmp_path):
    """create_session(kind='stage_guide') succeeds (AC-1)."""
    sessions_file = tmp_path / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))
    sid = coord.create_session(
        kind="stage_guide",
        owner_opencode_session_id="ses_test",
        goal={"intent": "guide-orchestrator", "last_seen_offset": 0},
    )
    assert sid.startswith("rds_")


def test_stage_guide_allows_parallel_stage_arch(tmp_path):
    """stage_guide + stage_arch can coexist (Oracle B1 bidirectional exemption)."""
    sessions_file = tmp_path / "sessions.json"
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))
    coord.create_session(kind="stage_guide", owner_opencode_session_id="ses_A",
                          goal={"intent": "guide-orchestrator", "last_seen_offset": 0})
    coord.create_session(kind="stage_arch", owner_opencode_session_id="ses_B",
                          goal={"intent": "guide-arch"})
    # No ConflictError — both should succeed


def test_stage_guide_extended_timeout(tmp_path):
    """stage_guide has 8h heartbeat timeout (AC-3)."""
    from skills.rddf_session.scripts.rddf_session_pkg._types import HEARTBEAT_TIMEOUT_BY_KIND
    assert HEARTBEAT_TIMEOUT_BY_KIND["stage_guide"] >= 8 * 60 * 60
    assert HEARTBEAT_TIMEOUT_BY_KIND["stage_arch"] == 30 * 60  # existing behavior preserved
```

- [ ] **Step 2**: Write failing test in `tests/unit/test_events_log.py`:

```python
"""Tests for events_log.py — events.jsonl append/read/archive."""
import json
import os
import pytest
from skills.rddf_session.scripts.events_log import EventsLog, archive_events


def test_append_event_writes_correct_format(tmp_path):
    """append_event produces valid JSONL row."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    log.append_event(
        event_type="phase_started",
        severity="info",
        message="test event",
        session_id="rds_xxx",
        kind="stage_arch",
        parent_session_id=None,
        owner_opencode_session_id="ses_test",
    )
    lines = (tmp_path / "events.jsonl").read_text().strip().split("\n")
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["event_type"] == "phase_started"
    assert row["context"]["session_id"] == "rds_xxx"


def test_read_since_filters_by_offset(tmp_path):
    """read_since(offset=N) returns only events at line > N."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    for i in range(5):
        log.append_event(event_type="test", severity="info", message=f"event-{i}",
                         session_id=f"rds_{i}", kind="stage_arch",
                         parent_session_id=None, owner_opencode_session_id="ses")
    rows = log.read_since(offset=2)
    assert len(rows) == 3


def test_archive_events_moves_old(tmp_path):
    """archive_events(keep=N) moves oldest rows beyond N to .archive.jsonl."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    for i in range(10):
        log.append_event(event_type="test", severity="info", message=f"e-{i}",
                         session_id=f"rds_{i}", kind="stage_arch",
                         parent_session_id=None, owner_opencode_session_id="ses")
    archive_events(str(tmp_path / "events.jsonl"), keep=3)
    main = (tmp_path / "events.jsonl").read_text().strip().split("\n")
    archive = (tmp_path / "events.archive.jsonl").read_text().strip().split("\n")
    assert len(main) == 3
    assert len(archive) == 7


def test_no_event_log_jsonl_alias(tmp_path):
    """Anti-pattern guard: events_log.py never creates event-log.jsonl (with hyphen, not events.jsonl)."""
    log = EventsLog(str(tmp_path / "events.jsonl"))
    log.append_event(event_type="test", severity="info", message="x",
                     session_id="r1", kind="stage_arch",
                     parent_session_id=None, owner_opencode_session_id="ses")
    # Must NOT have event-log.jsonl (only events.jsonl)
    assert not (tmp_path / "event-log.jsonl").exists()
```

- [ ] **Step 3**: Run `pytest tests/unit/test_sessions_schema_v3.py tests/unit/test_events_log.py -q` — verify all 10 tests FAIL.

### Task 1.2: Implement schema upgrade
- [ ] **Step 4**: Edit `_lib/schemas/sessions_schema.json` — bump `version` description to mention v3; add `"stage_guide"` to `kind` enum; add `"guide-orchestrator"` to `intent` enum; add `goal.last_seen_offset` field (integer, optional).
- [ ] **Step 5**: Verify schema is valid JSON (jq .).

### Task 1.3: Implement _types.py extensions
- [ ] **Step 6**: Edit `skills/rddf-session/scripts/rddf_session_pkg/_types.py`:
  - Add `"stage_guide"` and `"guide-orchestrator"` to `_VALID_KINDS`
  - Add `"guide-orchestrator": "stage_guide"` to `_KIND_ALIAS`
  - Add `HEARTBEAT_TIMEOUT_BY_KIND` dict (8h for guide, 30min for stages)

### Task 1.4: Implement _commands.py changes
- [ ] **Step 7**: Edit `skills/rddf-session/scripts/rddf_session_pkg/_commands.py`:
  - In `create_session()`, replace singleton check (line 84-94) with bidirectional exemption: skip if `existing["kind"] == "stage_guide" or kind == "stage_guide"`
  - Extend `list_sessions()` to accept optional `owner_opencode_session_id` and `state` params
  - Modify `check_heartbeat_timeouts()` to accept `readonly: bool = False` param + use `HEARTBEAT_TIMEOUT_BY_KIND` with fallback to config

### Task 1.5: Implement events_log.py module
- [ ] **Step 8**: Create `skills/rddf-session/scripts/events_log.py`:
  - `class EventsLog(path)`: with `append_event()`, `read_since(offset)`, `mark_seen(event_id, owner)`, `archive_events(keep)`
  - fcntl.flock + atomic write
  - 50MB cap enforcement (move oldest to .archive.jsonl when exceeded)
  - 7 event types: `phase_started` / `phase_completed` / `phase_failed` / `phase_heartbeat` / `guide_intent_detected` / `guide_routed` / `user_message`

### Task 1.6: Verify pass
- [ ] **Step 9**: Run `pytest tests/unit/test_sessions_schema_v3.py tests/unit/test_events_log.py -q` — verify all 10 tests PASS.
- [ ] **Step 10**: Run `./test.sh --quick` — verify no NEW failures.
- [ ] **Step 11**: Commit PR 1: `feat(rddf-session): add stage_guide kind + events.jsonl module (PR 1/4)` (worktree-internal).

---

## PR 2: hooks + parent + consumer 迁移

### Task 2.1: Write failing tests
- [ ] **Step 1**: Write `tests/integration/test_parent_kind_map.bats` with 3 tests (owner-scoped, stage_arch null when no guide, 2-level chain).
- [ ] **Step 2**: Write `tests/integration/test_rddf_stage_event.bats` with 3 tests (entry writes phase_started, close writes phase_completed, error writes phase_failed).
- [ ] **Step 3**: Write `tests/integration/test_monitor_cmd_extended_events.bats` with 2 tests (monitor reads extended events, fallback to event-log.jsonl).
- [ ] **Step 4**: Run bats — verify all 8 tests FAIL.

### Task 2.2: Implement
- [ ] **Step 5**: Edit `hooks.sh` parent_kind_map + owner-scoped lookup + write events + new guide hooks + fix detach bug.
- [ ] **Step 6**: Edit `monitor_cmd.py` — add events.jsonl first path, fallback to event-log.jsonl.
- [ ] **Step 7**: Run bats — verify all 8 tests PASS.
- [ ] **Step 8**: Run `./test.sh --quick` — verify no regression.
- [ ] **Step 9**: Commit PR 2.

---

## PR 3: guide 集成

### Task 3.1: Write failing tests
- [ ] **Step 1**: Write `tests/integration/test_guide_cross_container.bats` with 7 tests (creates stage_guide, close marks completed, two-owner sim, no-children skips read, renders since last_seen_offset, updates after render, scan-state no longer mutates).
- [ ] **Step 2**: Run bats — verify all 7 tests FAIL.

### Task 3.2: Implement
- [ ] **Step 3**: Edit `guide_entry.sh` — create stage_guide on launch, polling contract, close on exit.
- [ ] **Step 4**: Edit `scan-state.sh` — REMOVE check_heartbeat_timeouts call at line 535.
- [ ] **Step 5**: Run bats — verify all 7 tests PASS.
- [ ] **Step 6**: Run `./test.sh --quick` — verify no regression.
- [ ] **Step 7**: Commit PR 3.

---

## PR 4: docs + doctor + archive

### Task 4.1: Write failing tests
- [ ] **Step 1**: Write `tests/integration/test_doctor_state_json.bats` with 3 tests.
- [ ] **Step 2**: Run bats — verify all 3 tests FAIL.

### Task 4.2: Implement
- [ ] **Step 3**: Edit `state_schema_check.py` — add events.jsonl to `_STATE_FILES`, add 2 assertions.
- [ ] **Step 4**: Edit `docs/architecture/multi-session.md` — add Cross-Container Event Bus section.
- [ ] **Step 5**: Update CHANGELOG.md, USAGE.md, AGENTS.md, ADR-0055 status.
- [ ] **Step 6**: Run bats — verify all 3 tests PASS.
- [ ] **Step 7**: Run `./test.sh --full --regression` — verify all green.
- [ ] **Step 8**: Commit PR 4.
- [ ] **Step 9**: Run `openspec archive feat-guide-orchestrator-session-event-bus` (per rdd-builder archive flow).

---

## Worktree Setup (PR 0)

Before PR 1:
- [ ] Run `git worktree add .rddf/wt/feat-guide-orchestrator-session-event-bus -b feat/guide-orchestrator-session-event-bus` (existing `.rddf/wt/test-change` is busy → worktree mode per ADR-0048)
- [ ] Switch to worktree path for all subsequent work
- [ ] Verify `git status` shows clean master + new worktree branch

## Rollback Path

```bash
export RDDF_GUIDE_SESSION_ENABLED=false  # disable stage_guide creation
export RDDF_EVENTS_LOG_ENABLED=false     # stop event writes
git revert <PR-1-commit>                # schema rollback to v2
```

## Regression Gate

After PR 4:
- `./test.sh --full --regression` MUST return 0 or baseline-only-known-failures
- No NEW failures vs `tests/KNOWN_FAILURES.txt`