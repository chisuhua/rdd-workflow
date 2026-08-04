# archive-history-keep-semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit `--archive-orphans` flag to `rddf-session archive-history` so orphaned sessions are archived regardless of the `keep` budget, while non-orphan terminal sessions still respect `keep`, and make the command output distinguish kept active / kept terminal / archived counts.

**Architecture:** Extend `RddfSessionCommands.archive_history` with an `archive_orphans: bool` parameter that separates orphaned sessions from other terminal sessions, archives orphaned ones when the flag is true, and keeps the state machine unchanged (`orphaned` stays in `_TERMINAL_STATES`). Thread the flag through the `RddfSessionCoordinator` facade and the `rddf-session archive-history` bash parser in `skills/rddf-session/SKILL.md`, then update the skill documentation.

**Tech Stack:** Python 3.11+, pytest, bash (the `rddf-session` skill wrapper in `SKILL.md`).

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rddf-session/scripts/rddf_session_pkg/_commands.py` | Core `archive_history` archive-orphans logic |
| `skills/rddf-session/scripts/rddf_session.py` | Facade pass-through of `archive_orphans` to `_commands` |
| `skills/rddf-session/SKILL.md` | User-facing `archive-history` CLI: parse `--archive-orphans`, print clearer counts, document keep semantics |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_rddf_session_archive_orphans.py` | Unit tests for orphan cleanup regardless of keep and keep-boundary behavior |

---

### Task 1: Implement `archive_orphans` in `RddfSessionCommands.archive_history` and add unit tests

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session_pkg/_commands.py:279-306`
- Create: `tests/unit/test_rddf_session_archive_orphans.py`

- [x] **Step 1: Write the failing tests**

Create `tests/unit/test_rddf_session_archive_orphans.py` with the following content:

```python
"""Unit tests for archive_history archive_orphans semantics.

Covers the proposal scenarios:
- --archive-orphans archives every orphaned session regardless of keep budget
- without --archive-orphans, orphaned sessions stay when total terminal is below keep
"""
import json
from pathlib import Path

import pytest

from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator


def _terminal_session(index: int, state: str) -> dict:
    """Return a minimal valid session dict for the given terminal state."""
    return {
        "session_id": f"rds_{index:012x}",
        "kind": "stage_arch",
        "owner_opencode_session_id": "prev_owner",
        "state": state,
        "started_at": f"2026-07-{index + 1:02d}T00:00:00",
        "last_heartbeat": f"2026-07-{index + 1:02d}T01:00:00",
        "ended_at": f"2026-07-{index + 1:02d}T02:00:00",
        "end_reason": "heartbeat-timeout" if state == "orphaned" else "arch-done",
        "goal": {"intent": "guide-arch"},
        "attached_changes": [],
        "context_pointer": None,
    }


@pytest.fixture
def sessions_file(tmp_path):
    return tmp_path / "sessions.json"


@pytest.fixture
def coordinator(sessions_file):
    return RddfSessionCoordinator(sessions_file=str(sessions_file))


def test_archive_orphans_archives_all_orphaned_sessions_regardless_of_keep(coordinator, sessions_file):
    """archive_history(archive_orphans=True) MUST archive every orphaned session even when keep exceeds terminal count."""
    sessions_file.write_text(json.dumps({
        "version": 1,
        "sessions": [_terminal_session(i, "orphaned") for i in range(5)],
    }))
    active_sid = coordinator.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_active",
        goal={},
    )

    archived = coordinator.archive_history(keep=20, archive_orphans=True)

    assert archived == 5
    remaining = coordinator.list_sessions()
    assert [s.session_id for s in remaining] == [active_sid]
    assert all(s.state != "orphaned" for s in remaining)


def test_archive_orphans_false_keeps_orphaned_within_keep_budget(coordinator, sessions_file):
    """archive_history(archive_orphans=False) MUST keep orphaned sessions when total terminal count is below keep."""
    sessions_file.write_text(json.dumps({
        "version": 1,
        "sessions": [_terminal_session(i, "orphaned") for i in range(5)],
    }))
    active_sid = coordinator.create_session(
        kind="stage_plan",
        owner_opencode_session_id="ses_active",
        goal={},
    )

    archived = coordinator.archive_history(keep=20, archive_orphans=False)

    assert archived == 0
    remaining = coordinator.list_sessions()
    assert len(remaining) == 6  # 5 orphaned + 1 active
    assert active_sid in {s.session_id for s in remaining}
```

- [x] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_rddf_session_archive_orphans.py -v`

Expected: FAIL with `TypeError: RddfSessionCommands.archive_history() got an unexpected keyword argument 'archive_orphans'` (and the same error on the coordinator facade).

- [x] **Step 3: Write the minimal implementation**

In `skills/rddf-session/scripts/rddf_session_pkg/_commands.py`, replace the `archive_history` method (lines 279-306) with:

```python
    def archive_history(
        self, keep: int = 20, archive_orphans: bool = False
    ) -> int:
        """Move old terminal sessions to .archive.json.

        Non-orphan terminal sessions (completed / failed / abandoned) are
        kept up to ``keep`` most-recent by ``ended_at``. When
        ``archive_orphans`` is True, sessions in the ``orphaned`` state
        are archived regardless of the keep budget. Active sessions are
        never archived. The state machine is unchanged: ``orphaned``
        remains in ``_TERMINAL_STATES``.
        """
        archive_path = self._store._sessions_file.with_suffix(".archive.json")
        if archive_path.exists():
            archive_data = json.loads(archive_path.read_text())
        else:
            archive_data = {"version": 1, "sessions": []}

        def _do_archive():
            nonlocal archive_data
            data = self._store.read_unlocked()
            active = [s for s in data["sessions"] if s["state"] not in _TERMINAL_STATES]
            orphaned = [s for s in data["sessions"] if s["state"] == "orphaned"]
            terminal_non_orphan = [
                s for s in data["sessions"]
                if s["state"] in _TERMINAL_STATES and s["state"] != "orphaned"
            ]
            terminal_non_orphan.sort(
                key=lambda s: s.get("ended_at") or "", reverse=True
            )
            kept_terminal = terminal_non_orphan[:keep]
            to_archive = terminal_non_orphan[keep:]
            if archive_orphans:
                to_archive.extend(orphaned)
            else:
                kept_terminal.extend(orphaned)

            archive_data["sessions"].extend(to_archive)
            archive_data["updated_at"] = _now()
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            with archive_path.open("w") as f:
                json.dump(archive_data, f, indent=2)

            data["sessions"] = active + kept_terminal
            data["updated_at"] = _now()
            self._store.atomic_write(data)
            return len(to_archive)
        return self._store.with_file_lock(_do_archive)
```

In `skills/rddf-session/scripts/rddf_session.py`, update the facade to pass the flag through. Change lines 119-120 from:

```python
    def archive_history(self, keep: int = 20) -> int:
        return self._commands.archive_history(keep)
```

to:

```python
    def archive_history(self, keep: int = 20, archive_orphans: bool = False) -> int:
        return self._commands.archive_history(keep, archive_orphans=archive_orphans)
```

- [x] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_rddf_session_archive_orphans.py -v`

Expected: both tests PASS.

- [x] **Step 5: Defer commit**

本 change 按仓库约定不逐任务 commit; execute 完成后统一在 archive 阶段提交.

---

### Task 2: Update `rddf-session archive-history` CLI and documentation

**Files:**
- Modify: `skills/rddf-session/SKILL.md` (archive-history subcommand, subcommand list, and keep/orphan documentation)

- [x] **Step 1: Write the failing verification script**

Create a temporary throwaway script at `/tmp/opencode/archive_history_cli_check.sh` with the following content. It replicates the `archive-history` CLI path so we can verify `--archive-orphans` is accepted before updating `SKILL.md`:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/tmp/opencode/archive_history_cli_check"
rm -rf "$PROJECT_ROOT"
mkdir -p "$PROJECT_ROOT/.rddf/state"
cd "$PROJECT_ROOT"
git init -q

export PROJECT_ROOT
python3 <<'PYEOF'
import sys
sys.path.insert(0, "/workspace/project/rdd-workflow")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
c = RddfSessionCoordinator(sessions_file=f"{PROJECT_ROOT}/.rddf/state/sessions.json")
for i in range(3):
    sid = c.create_session(kind="stage_arch", owner_opencode_session_id=f"owner_{i}", goal={})
    c.update_session_status(sid, "completed", end_reason="x")
    data = c._store.read_unlocked()
    for s in data["sessions"]:
        if s["session_id"] == sid:
            s["state"] = "orphaned"
            s["end_reason"] = "heartbeat-timeout"
    c._store.atomic_write(data)
active_sid = c.create_session(kind="stage_plan", owner_opencode_session_id="active_owner", goal={})
print(f"active_sid={active_sid}")
PYEOF

SESSIONS_FILE="$PROJECT_ROOT/.rddf/state/sessions.json"
KEEP=20
ARCHIVE_ORPHANS="yes"
ARCHIVE_ORPHANS="$ARCHIVE_ORPHANS" python3 - "$SESSIONS_FILE" "$KEEP" "$PROJECT_ROOT" <<'PYEOF'
import sys, os
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else ".")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator, _TERMINAL_STATES
sessions_file = sys.argv[1]
keep = int(sys.argv[2])
archive_orphans = os.environ.get("ARCHIVE_ORPHANS") == "yes"
coord = RddfSessionCoordinator(sessions_file=sessions_file)
n = coord.archive_history(keep=keep, archive_orphans=archive_orphans)
after = coord.list_sessions()
active_kept = sum(1 for s in after if s.state not in _TERMINAL_STATES)
terminal_kept = sum(1 for s in after if s.state in _TERMINAL_STATES)
print(f"Archived {n} sessions ({active_kept} active kept, {terminal_kept} terminal kept)")
PYEOF
```

The script expects to print `Archived 3 sessions (1 active kept, 0 terminal kept)` once the CLI supports `--archive-orphans` and the output format is updated.

- [x] **Step 2: Run the verification script to verify it fails**

Run:

```bash
chmod +x /tmp/opencode/archive_history_cli_check.sh
bash /tmp/opencode/archive_history_cli_check.sh
```

Expected: FAIL. The `ARCHIVE_ORPHANS` environment variable is ignored because the current `SKILL.md` parser does not recognize `--archive-orphans`, so `archive_history` is called with the default `archive_orphans=False`, printing `Archived 0 sessions (1 active kept, 3 terminal kept)` instead of the expected `Archived 3 sessions (1 active kept, 0 terminal kept)`.

- [x] **Step 3: Update the CLI and docs in `SKILL.md`**

1. In the **Subcommands** block (around line 30), add the `--archive-orphans` example. The block should read:

```markdown
skill_use("rddf-session archive-history")                       # move old terminal sessions to .archive.json (default keep=20)
skill_use("rddf-session archive-history --keep=50")           # custom keep count
skill_use("rddf-session archive-history --archive-orphans")   # archive orphaned sessions regardless of keep
```

2. In the **Implementation (Bash)** `archive-history)` case (around line 257-276), replace it with:

```bash
    archive-history)
        KEEP=20
        ARCHIVE_ORPHANS=""
        while [[ $# -gt 0 ]]; do
            case "$1" in
                --keep=*) KEEP="${1#*=}" ;;
                --archive-orphans) ARCHIVE_ORPHANS="yes" ;;
                *) shift ;;
            esac
            shift || break
        done
        ARCHIVE_ORPHANS="$ARCHIVE_ORPHANS" python3 - "$SESSIONS_FILE" "$KEEP" "$PROJECT_ROOT" <<'PYEOF'
import sys
import os
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else ".")
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator, _TERMINAL_STATES
sessions_file = sys.argv[1]
keep = int(sys.argv[2])
archive_orphans = os.environ.get("ARCHIVE_ORPHANS") == "yes"
coord = RddfSessionCoordinator(sessions_file=sessions_file)
n = coord.archive_history(keep=keep, archive_orphans=archive_orphans)
after = coord.list_sessions()
active_kept = sum(1 for s in after if s.state not in _TERMINAL_STATES)
terminal_kept = sum(1 for s in after if s.state in _TERMINAL_STATES)
print(f"Archived {n} sessions ({active_kept} active kept, {terminal_kept} terminal kept)")
PYEOF
        ;;
```

3. Add a new section after the existing **Status Subcommand** section (or near the end of the document) explaining keep semantics and orphaned cleanup. Insert:

```markdown
## Archive-History Keep Semantics

`archive-history` moves terminal sessions (`completed`, `failed`, `abandoned`, `orphaned`) from `.rddf/state/sessions.json` to `.rddf/state/sessions.archive.json`.

- ``keep=N`` (default 20): retain the N most-recent non-orphan terminal sessions by `ended_at`. Active sessions are always retained and never counted against the keep budget.
- `--archive-orphans`: explicitly archive all sessions in the `orphaned` state, regardless of the keep budget. This is useful when orphaned sessions have accumulated and the default keep value is larger than the total terminal count, because without this flag orphaned sessions are treated as ordinary terminal sessions and are kept alongside the recent N.
- Auto-archive hooks (entry/close) still call `archive_history` with the default `archive_orphans=False`, preserving existing behavior.
```

- [x] **Step 4: Run the verification script and unit tests to verify everything passes**

Run the verification script again:

```bash
bash /tmp/opencode/archive_history_cli_check.sh
```

Expected: prints `Archived 3 sessions (1 active kept, 0 terminal kept)`.

Then run the unit tests to confirm no regressions:

```bash
python3 -m pytest tests/unit/test_rddf_session.py tests/unit/test_rddf_session_archive_orphans.py -q --tb=short
```

Expected: all tests PASS.

- [x] **Step 5: Defer commit**

本 change 按仓库约定不逐任务 commit; execute 完成后统一在 archive 阶段提交.

---

## Self-Review Checklist

1. **Spec coverage**: The proposal requires `--archive-orphans`, clearer output, docs, and 1-2 unit tests. All are covered in Task 1 and Task 2.
2. **No placeholders**: No `TBD`, `TODO`, `implement later`, or `similar to Task N` wording appears above.
3. **Type consistency**: `archive_orphans: bool` is used in `_commands.py`, `rddf_session.py`, and the `SKILL.md` Python wrapper. The return type remains `int` (number of archived sessions), preserving backward compatibility with existing callers such as `rddf_session_hooks.sh`.
