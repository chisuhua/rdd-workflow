# fix-scan-state-binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the broken `scan_session_binding()` owner variable syntax, split the heartbeat GC call into a reusable shell helper, and wire owner-based current-session detection into the dashboard collector.

**Architecture:** Fix `skills/guide/scripts/scan-state.sh` so it derives a clean `owner` string and introduces `check_heartbeat_timeouts()` as a standalone function that `scan_session_binding()` calls before binding lookup. Update `skills/_lib/dashboard/__init__.py::collect()` to use `OPENCODE_SESSION_ID` to mark the owner-matching session as `is_current`, with a fallback to the most-recent active session. Lock the behavior with a new bats regression test and a Python unit test.

**Tech Stack:** bash 4+, Python 3.11, bats-core, pytest.

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/guide/scripts/scan-state.sh` | Repair `owner` syntax, extract `check_heartbeat_timeouts()`, and call it from `scan_session_binding()` |
| `skills/_lib/dashboard/__init__.py` | Mark `is_current` by `owner_opencode_session_id` matching `OPENCODE_SESSION_ID` |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_fix_scan_state_binding.bats` | Regression: syntax fix, heartbeat helper flow, and binding output |
| `tests/unit/test_dashboard_renderer.py` | `collect()` owner-based current marking + active fallback |

---

## Task 1: Fix `scan-state.sh` syntax and add heartbeat helper

**Files:**
- Modify: `skills/guide/scripts/scan-state.sh:222-257`
- Test: `tests/integration/test_fix_scan_state_binding.bats`

- [ ] **Step 1: Write the failing test**

Add a bats test that sources `scan-state.sh` and calls `scan_session_binding` with a mocked `sessions.json` containing a session whose `owner_opencode_session_id` equals `OPENCODE_SESSION_ID`. Before the fix, the test will fail because the broken `owner` variable is polluted by the comment line, so binding lookup misses.

```bash
@test "scan_session_binding: returns current binding when owner matches" {
    _write_sessions
    run bash -c "
        export OPENCODE_SESSION_ID='omo_ses_owner_001'
        source '$REPO_ROOT/skills/guide/scripts/scan-state.sh'
        scan_session_binding '$PWD'
        printf '%s\n' \"\${BINDING_LINES[@]}\"
    "
    [ \"$status\" -eq 0 ]
    [[ \"$output\" == *\"Current:\"* ]]
    [[ \"$output\" == *\"rds_abc123\"* ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_fix_scan_state_binding.bats`
Expected: FAIL — `BINDING_LINES` is empty or the command errors with the syntax/import problems.

- [ ] **Step 3: Write minimal implementation**

In `skills/guide/scripts/scan-state.sh`:

1. Replace the broken `owner` block with a single-line assignment:

```bash
local owner="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
```

2. Add a new `check_heartbeat_timeouts()` helper that loads `RddfSessionCoordinator` and calls `coord.check_heartbeat_timeouts()`:

```bash
# check_heartbeat_timeouts [PROJECT_ROOT]
#   Scans sessions.json and marks timed-out active sessions as orphaned.
#   Requires a python3 environment with the repo root available for import.
check_heartbeat_timeouts() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local SESSIONS_FILE="$PROJECT_ROOT/.rddf/state/sessions.json"
  [ -f "$SESSIONS_FILE" ] || return 0
  local SCRIPT_DIR
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd 2>/dev/null)" || SCRIPT_DIR=""
  local PYTHON_PATH="${SCRIPT_DIR:+$(cd "$SCRIPT_DIR/../.." && pwd)}"
  PY_PROJECT_ROOT="$PROJECT_ROOT" \
  python3 - "$SESSIONS_FILE" "${PYTHON_PATH:-$PROJECT_ROOT}" <<'PYEOF'
import os, sys, importlib.util
sys.path.insert(0, sys.argv[2] if len(sys.argv) > 2 else ".")
module_path = os.path.join(sys.argv[2], "skills", "rddf-session", "scripts", "rddf_session.py")
spec = importlib.util.spec_from_file_location("rddf_session", module_path)
rddf_session = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rddf_session)
RddfSessionCoordinator = rddf_session.RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=sys.argv[1])
coord.check_heartbeat_timeouts()
PYEOF
}
```

3. Update `scan_session_binding()` to call `check_heartbeat_timeouts "$PROJECT_ROOT"` before reading binding lines, and remove the `coord.check_heartbeat_timeouts()` call from the heredoc.

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_fix_scan_state_binding.bats`
Expected: PASS — `BINDING_LINES` contains the current session.

- [ ] **Step 5: Commit**

```bash
git add skills/guide/scripts/scan-state.sh tests/integration/test_fix_scan_state_binding.bats
git commit -m "fix(scan-state): repair owner syntax and split heartbeat helper"
```

---

## Task 2: Wire owner-based `is_current` into dashboard `collect()`

**Files:**
- Modify: `skills/_lib/dashboard/__init__.py:290-315`
- Test: `tests/unit/test_dashboard_renderer.py`

- [ ] **Step 1: Write the failing test**

Add two tests in `tests/unit/test_dashboard_renderer.py` under a new `TestCollectCurrentSession` class. They mock the state_reader functions and exercise `collect()` with and without `OPENCODE_SESSION_ID`.

```python
class TestCollectCurrentSession:
    def _patch_readers(self, monkeypatch, sessions):
        monkeypatch.setattr(dashboard, "read_arch_handoff", lambda _p: None)
        monkeypatch.setattr(dashboard, "read_plan_handoff", lambda _p: None)
        monkeypatch.setattr(dashboard, "read_iteration", lambda _p: None)
        monkeypatch.setattr(dashboard, "read_roadmap_state", lambda _p: None)
        monkeypatch.setattr(dashboard, "read_proposal_suggestions", lambda _p: None)
        monkeypatch.setattr(dashboard, "list_worktrees", lambda: [])
        monkeypatch.setattr(dashboard, "list_change_dirs", lambda _p: [])
        monkeypatch.setattr(dashboard, "read_sessions", lambda _p: sessions)

    def test_collect_marks_owner_session_as_current(self, monkeypatch, tmp_path):
        sessions = [
            {
                "session_id": "s1",
                "kind": "plan",
                "state": "active",
                "owner_opencode_session_id": "owner_a",
                "started_at": "2026-07-21T10:00:00+00:00",
            },
            {
                "session_id": "s2",
                "kind": "ship",
                "state": "active",
                "owner_opencode_session_id": "owner_b",
                "started_at": "2026-07-21T11:00:00+00:00",
            },
        ]
        self._patch_readers(monkeypatch, sessions)
        monkeypatch.setenv("OPENCODE_SESSION_ID", "owner_a")
        data = collect(str(tmp_path))
        by_id = {s.session_id: s for s in data.sessions}
        assert by_id["s1"].is_current is True
        assert by_id["s2"].is_current is False

    def test_collect_falls_back_to_most_recent_active(self, monkeypatch, tmp_path):
        sessions = [
            {
                "session_id": "s1",
                "kind": "plan",
                "state": "active",
                "owner_opencode_session_id": "owner_a",
                "started_at": "2026-07-21T10:00:00+00:00",
            },
            {
                "session_id": "s2",
                "kind": "ship",
                "state": "active",
                "owner_opencode_session_id": "owner_b",
                "started_at": "2026-07-21T11:00:00+00:00",
            },
        ]
        self._patch_readers(monkeypatch, sessions)
        monkeypatch.delenv("OPENCODE_SESSION_ID", raising=False)
        data = collect(str(tmp_path))
        by_id = {s.session_id: s for s in data.sessions}
        assert by_id["s2"].is_current is True
        assert by_id["s1"].is_current is False
```

Expected: Before wiring, the owner-based test fails (`is_current=False` for the owned session); the fallback test already passes.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_dashboard_renderer.py::TestCollectCurrentSession::test_collect_marks_owner_session_as_current -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

In `skills/_lib/dashboard/__init__.py` inside `collect()`, after reading sessions, replace the active-only logic with owner-first detection:

```python
owner_id = os.environ.get("OPENCODE_SESSION_ID")
current_id = None
if owner_id:
    owned = [
        s for s in sessions
        if s.get("owner_opencode_session_id") == owner_id
        and s.get("state") != "abandoned"
    ]
    owned.sort(key=lambda s: s.get("started_at") or "", reverse=True)
    if owned:
        current_id = owned[0].get("session_id")
if current_id is None:
    active = [s for s in sessions if s.get("state") == "active"]
    active.sort(key=lambda s: s.get("started_at") or "", reverse=True)
    current_id = active[0].get("session_id") if active else None
```

Keep the rest of the SessionEntry loop unchanged.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_dashboard_renderer.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/dashboard/__init__.py tests/unit/test_dashboard_renderer.py
git commit -m "feat(dashboard): mark current session by owner binding"
```

---

## Task 3: Verify no regressions and update tasks.md

**Files:**
- Modify: `openspec/changes/fix-scan-state-binding/tasks.md`

- [ ] **Step 1: Write the failing test**

Run the full test suite (bats + pytest) and confirm any failures before marking tasks complete.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test && pytest tests/unit/ -q`
Expected: Tests may fail or show incomplete tasks until the change is fully complete.

- [ ] **Step 3: Write minimal implementation**

Mark all completed tasks in `tasks.md` as `- [x]`. Ensure the syntax/import/heartbeat and dashboard changes are in place.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
npm test
pytest tests/unit/ -q
pytest tests/integration/ -q
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add openspec/changes/fix-scan-state-binding/tasks.md
git commit -m "docs(fix-scan-state-binding): mark tasks complete"
```

---

## Self-Review

1. **Spec coverage**: proposal.md asks for syntax fix, `check_heartbeat_timeouts` wiring, dashboard binding, and bats test. All covered.
2. **Placeholder scan**: No TBD/TODO/"implement later" in this plan.
3. **Type consistency**: `owner_opencode_session_id` is used consistently in `scan_session_binding`, `RddfSessionCoordinator`, and `collect()`.
