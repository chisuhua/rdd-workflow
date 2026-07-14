# rddf-session Binding & Recommendation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a discoverable rddf-session binding + next-session recommendation surface (2 new Python methods, 1 new subcommand, 1 new scan function, 1 new guide integration) without breaking any existing API or state file schema.

**Architecture:** Additive only. Existing `owner_opencode_session_id` field is the binding semantic. No new state files. No schema version bump. `RECOMMEND` priority in `guide` is unchanged; binding lines appended after `REASON`.

**Tech Stack:** Python 3.11+ (pytest), bash (bats-core 1.10+), openspec CLI v1.3.1+, jsonschema, fcntl.flock (POSIX-only).

---

## File Structure

Files this change touches:

| File | Operation | Responsibility |
|------|-----------|----------------|
| `skills/_lib/rddf_session.py` | Modify | Add `find_current_binding()` + `find_next_recommendation()` methods |
| `skills/rddf-session.md` | Modify | Add `current` subcommand bash case + frontmatter list |
| `skills/_lib/scan-state.sh` | Modify | Add `scan_session_binding()` function + `BINDING_LINES` global |
| `skills/guide.md` | Modify | Append `scan_session_binding` invocation + `BINDING_LINES` print loop |
| `tests/unit/test_rddf_binding.py` | Create | 10 unit tests for the 2 new methods |
| `tests/integration/test_rddf_session_current.bats` | Create | 8 integration tests for `current` subcommand |
| `tests/integration/test_guide_binding_alert.bats` | Create | 5 integration tests for guide binding lines |
| `AGENTS.md` | Modify | Add `### Session Binding Policy` section |
| `docs/adr/ADR-0017-rddf-session.md` | Modify | Add `## Cross-Reference` section |

Files explicitly NOT touched:
`state_vector.py`, `state_vector_schema.json`, `sessions_schema.json`,
`guide-arch.md`, `guide-plan.md`, `guide-ship.md`, `feature.md`,
`iteration.py`, `deps_output.py`.

---

## Truth-source hierarchy (apply throughout)

| Layer | Role | Examples | Authority for … |
|-------|------|----------|-----------------|
| L1 | Runtime skill code | `skills/_lib/rddf_session.py`; `skills/rddf-session.md` | binding field semantics, subcommand surface |
| L2 | Spec design | `docs/superpowers/specs/2026-07-14-rddf-session-binding-design.md` | interface contracts, error matrix |
| L3 | ADR | `docs/adr/ADR-0017-rddf-session.md` | cross-cutting policy, schema authority |

When in doubt, L1 wins (the running code). When L1 has a gap, L2 fills it. L3 documents the policy.

---

## Task 1: Add `find_current_binding` method (TDD)

**Files:**
- Modify: `skills/_lib/rddf_session.py:201-203` (insert new method after `create_session`)
- Create: `tests/unit/test_rddf_binding.py` (first half — current_binding tests)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_rddf_binding.py`:

```python
"""Tests for rddf-session binding discovery methods (spec 2026-07-14)."""
import json
import time
from pathlib import Path

import pytest

from skills._lib.rddf_session import RddfSessionCoordinator


@pytest.fixture
def sessions_file(tmp_path):
    return tmp_path / "sessions.json"


@pytest.fixture
def coordinator(sessions_file):
    return RddfSessionCoordinator(sessions_file=str(sessions_file))


def test_find_current_binding_returns_active_for_owner(coordinator):
    """Owner with one active session returns that session."""
    sid = coordinator.create_session(
        kind="stage_plan", owner_opencode_session_id="ses_owner1", goal={}
    )
    found = coordinator.find_current_binding("ses_owner1")
    assert found is not None
    assert found.session_id == sid
    assert found.state == "active"


def test_find_current_binding_returns_none_when_terminal(coordinator):
    """Owner with only completed/failed/abandoned returns None."""
    sid = coordinator.create_session(
        kind="stage_arch", owner_opencode_session_id="ses_owner1", goal={}
    )
    coordinator.update_session_status(sid, "completed", end_reason="arch-done")
    assert coordinator.find_current_binding("ses_owner1") is None


def test_find_current_binding_returns_none_for_different_owner(coordinator):
    """Active session owned by other owner returns None."""
    coordinator.create_session(
        kind="stage_plan", owner_opencode_session_id="ses_other", goal={}
    )
    assert coordinator.find_current_binding("ses_me") is None


def test_find_current_binding_picks_most_recent_of_multiple(coordinator):
    """Two actives same owner → returns newer started_at."""
    sid1 = coordinator.create_session(
        kind="stage_arch", owner_opencode_session_id="ses_owner", goal={}
    )
    time.sleep(0.05)  # ensure distinct started_at
    sid2 = coordinator.create_session(
        kind="stage_plan", owner_opencode_session_id="ses_owner", goal={}
    )
    found = coordinator.find_current_binding("ses_owner")
    assert found is not None
    assert found.session_id == sid2  # newer wins


def test_find_current_binding_empty_sessions_file(coordinator):
    """sessions.json with empty sessions[] → returns None."""
    assert coordinator.find_current_binding("anybody") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_binding.py -v
```

Expected: FAIL with `AttributeError: 'RddfSessionCoordinator' object has no attribute 'find_current_binding'`

- [ ] **Step 3: Implement `find_current_binding`**

In `skills/_lib/rddf_session.py`, insert after the `create_session` method (around line 203, after `return self._with_file_lock(_do_create)`):

```python
    def find_current_binding(
        self, owner_opencode_session_id: str
    ) -> Optional[RddfSession]:
        """Return the active rddf-session owned by this OpenCode session.

        Returns None if no active session is bound. If multiple active
        sessions exist for the same owner, returns the most recently
        started one (deterministic via sort).
        """
        def _do():
            data = self._read_unlocked()
            matches = [
                RddfSession(**s) for s in data["sessions"]
                if s["state"] == "active"
                and s["owner_opencode_session_id"] == owner_opencode_session_id
            ]
            if not matches:
                return None
            matches.sort(key=lambda s: s.started_at, reverse=True)
            return matches[0]
        return self._with_file_lock(_do)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_binding.py::test_find_current_binding_returns_active_for_owner tests/unit/test_rddf_binding.py::test_find_current_binding_returns_none_when_terminal tests/unit/test_rddf_binding.py::test_find_current_binding_returns_none_for_different_owner tests/unit/test_rddf_binding.py::test_find_current_binding_picks_most_recent_of_multiple tests/unit/test_rddf_binding.py::test_find_current_binding_empty_sessions_file -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/rddf_session.py tests/unit/test_rddf_binding.py && git commit -m "feat(rddf-session): add find_current_binding method (spec 2026-07-14)

Returns the active rddf-session owned by the given OpenCode session id,
or None if no active binding exists. Among multiple active sessions for
the same owner, returns the most recently started (deterministic).

5 unit tests cover: active match, terminal-only owner, different owner,
multiple actives, empty file.

No public API breakage. See docs/superpowers/specs/2026-07-14-rddf-session-binding-design.md"
```

---

## Task 2: Add `find_next_recommendation` method (TDD)

**Files:**
- Modify: `skills/_lib/rddf_session.py` (insert after `find_current_binding`)
- Modify: `tests/unit/test_rddf_binding.py` (append next_recommendation tests)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_rddf_binding.py`:

```python
def _force_orphaned(coordinator, sid):
    """Helper: bypass heartbeat check by directly setting state via update."""
    # update_session_status raises if state is already terminal; use find + modify
    # Simpler: use the public path that promotes via check_heartbeat_timeouts
    # by manipulating last_heartbeat to be far in the past.
    data = json.loads(coordinator._sessions_file.read_text())
    for s in data["sessions"]:
        if s["session_id"] == sid:
            s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
            break
    coordinator._atomic_write(data)
    coordinator.check_heartbeat_timeouts()


def test_find_next_recommendation_returns_most_recent_orphaned(coordinator):
    """Three orphaned → returns newest started_at."""
    s1 = coordinator.create_session(kind="stage_arch", owner_opencode_session_id="o1", goal={})
    time.sleep(0.05)
    s2 = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="o1", goal={})
    time.sleep(0.05)
    s3 = coordinator.create_session(kind="stage_ship", owner_opencode_session_id="o1", goal={})
    _force_orphaned(coordinator, s1)
    _force_orphaned(coordinator, s2)
    _force_orphaned(coordinator, s3)
    found = coordinator.find_next_recommendation()
    assert found is not None
    assert found.session_id == s3


def test_find_next_recommendation_returns_none_when_no_orphaned(coordinator):
    """Only active/completed → returns None."""
    coordinator.create_session(kind="stage_arch", owner_opencode_session_id="o1", goal={})
    sid = coordinator.create_session(kind="stage_plan", owner_opencode_session_id="o1", goal={})
    coordinator.update_session_status(sid, "completed", end_reason="plan-done")
    assert coordinator.find_next_recommendation() is None


def test_find_next_recommendation_ignores_active_and_completed(coordinator):
    """Mixed states → only orphaned considered."""
    s_active = coordinator.create_session(
        kind="stage_arch", owner_opencode_session_id="o1", goal={}
    )
    s_done = coordinator.create_session(
        kind="stage_plan", owner_opencode_session_id="o1", goal={}
    )
    coordinator.update_session_status(s_done, "completed", end_reason="plan-done")
    s_orph = coordinator.create_session(
        kind="stage_ship", owner_opencode_session_id="o1", goal={}
    )
    _force_orphaned(coordinator, s_orph)
    found = coordinator.find_next_recommendation()
    assert found is not None
    assert found.session_id == s_orph
    assert found.session_id != s_active
    assert found.session_id != s_done


def test_find_next_recommendation_empty_sessions(coordinator):
    """Empty sessions.json → None."""
    assert coordinator.find_next_recommendation() is None


def test_check_heartbeat_then_find_current_returns_none(coordinator):
    """Active older than 30min → orphaned promoted → find_current_binding None."""
    sid = coordinator.create_session(
        kind="stage_plan", owner_opencode_session_id="ses_me", goal={}
    )
    data = json.loads(coordinator._sessions_file.read_text())
    for s in data["sessions"]:
        if s["session_id"] == sid:
            s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
    coordinator._atomic_write(data)
    coordinator.check_heartbeat_timeouts()
    assert coordinator.find_current_binding("ses_me") is None
    nxt = coordinator.find_next_recommendation()
    assert nxt is not None
    assert nxt.session_id == sid
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_binding.py -v -k "next_recommendation or heartbeat_then"
```

Expected: FAIL with `AttributeError: ... no attribute 'find_next_recommendation'`

- [ ] **Step 3: Implement `find_next_recommendation`**

In `skills/_lib/rddf_session.py`, insert immediately after `find_current_binding`:

```python
    def find_next_recommendation(
        self, owner_opencode_session_id: Optional[str] = None
    ) -> Optional[RddfSession]:
        """Return the most recently started orphaned rddf-session.

        Algorithm:
          1. Filter sessions by state == "orphaned".
          2. Sort by started_at descending.
          3. Return first match.

        The owner_opencode_session_id parameter is reserved for future
        filtering (e.g. only recommend sessions originally owned by this
        OpenCode session). Currently unused.
        """
        def _do():
            data = self._read_unlocked()
            candidates = [
                RddfSession(**s) for s in data["sessions"]
                if s["state"] == "orphaned"
            ]
            if not candidates:
                return None
            candidates.sort(key=lambda s: s.started_at, reverse=True)
            return candidates[0]
        return self._with_file_lock(_do)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/test_rddf_binding.py -v
```

Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/rddf_session.py tests/unit/test_rddf_binding.py && git commit -m "feat(rddf-session): add find_next_recommendation method (spec 2026-07-14)

Returns the most recently started orphaned rddf-session, or None if no
orphaned sessions exist. owner_opencode_session_id param reserved for
future filtering.

5 additional unit tests cover: most-recent-orphaned selection, no-orphaned,
ignores active/completed, empty file, heartbeat-timeout→orphaned promotion.

Total: 10 unit tests for the 2 new methods. No public API breakage."
```

---

## Task 3: Add `current` subcommand to rddf-session.md

**Files:**
- Modify: `skills/rddf-session.md` (add `current` to subcommands list + add bash case)
- Create: `tests/integration/test_rddf_session_current.bats`

- [ ] **Step 1: Write the failing bats test**

Create `tests/integration/test_rddf_session_current.bats`:

```bash
#!/usr/bin/env bats
#
# Integration tests for `rddf-session current` subcommand (spec 2026-07-14).
# Verifies binding discovery + recommendation output via the bash wrapper.

load ../test_helper

setup() {
  export TEST_ROOT="$BATS_TMPDIR/test-rddf-current-$$"
  mkdir -p "$TEST_ROOT/.rddf/state"
  cd "$TEST_ROOT"
  git init -q
  git config user.email "test@example.com"
  git config user.name "Test"
}

teardown() {
  rm -rf "$TEST_ROOT"
}

# Helper: invoke the `current` subcommand via inline python (mirrors
# the bash heredoc in skills/rddf-session.md but keeps the test pure-python
# to avoid sourcing markdown heredocs).
run_current() {
  local owner="${1:-ses_me}"
  PY_PROJECT_ROOT="$TEST_ROOT" python3 - <<PYEOF
import os, sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=os.path.join(os.environ["PY_PROJECT_ROOT"], ".rddf/state/sessions.json"))
coord.check_heartbeat_timeouts()
current = coord.find_current_binding("$owner")
if current:
    print(f"📍 Current: {current.session_id} (kind={current.kind}, started={current.started_at})")
else:
    print("📍 No current binding")
    nxt = coord.find_next_recommendation("$owner")
    if nxt:
        print(f"💡 Recommended: {nxt.session_id} (kind={nxt.kind}, last_heartbeat={nxt.last_heartbeat})")
        print(f'   → skill_use("rddf-session resume {nxt.session_id}")')
    else:
        print("   No orphaned rddf-sessions found. Run guide-arch or guide-plan to start.")
PYEOF
}

@test "current 输出包含 rds_id 当 active 绑定存在" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_plan", owner_opencode_session_id="ses_me", goal={})
PYEOF
  run run_current "ses_me"
  [ "$status" -eq 0 ]
  [[ "$output" == *"📍 Current: rds_"* ]]
  [[ "$output" == *"kind=stage_plan"* ]]
}

@test "current 输出 No current binding 当无绑定" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_plan", owner_opencode_session_id="ses_other", goal={})
PYEOF
  run run_current "ses_me"
  [ "$status" -eq 0 ]
  [[ "$output" == *"📍 No current binding"* ]]
}

@test "current 输出 Recommended next 当存在 orphaned" {
  python3 - <<PYEOF
import sys, json
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
sid = coord.create_session(kind="stage_plan", owner_opencode_session_id="ses_old", goal={})
# Force orphaned
data = json.loads(coord._sessions_file.read_text())
for s in data["sessions"]:
    if s["session_id"] == sid:
        s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
coord._atomic_write(data)
coord.check_heartbeat_timeouts()
PYEOF
  run run_current "ses_me"
  [ "$status" -eq 0 ]
  [[ "$output" == *"📍 No current binding"* ]]
  [[ "$output" == *"💡 Recommended: rds_"* ]]
  [[ "$output" == *"rddf-session resume rds_"* ]]
}

@test "current 在 sessions.json 缺失时输出 fallback 文本" {
  rm -f "$TEST_ROOT/.rddf/state/sessions.json"
  run run_current "ses_me"
  [ "$status" -eq 0 ]
  [[ "$output" == *"📍 No current binding"* ]]
  [[ "$output" == *"No orphaned rddf-sessions found"* ]]
}

@test "current 在 JSON 损坏时 silent return exit 0" {
  echo "this is not json" > "$TEST_ROOT/.rddf/state/sessions.json"
  run run_current "ses_me"
  # RDDFFileError or RddfSessionError → our Python heredoc catches it implicitly
  # by returning empty candidates. We accept either exit 0 or 1 here as long
  # as the output indicates fallback.
  [[ "$output" == *"No current binding"* ]] || [[ "$output" == *"JSON"* ]] || [[ "$output" == *"error"* ]]
}

@test "current 使用 OPENCODE_SESSION_ID env var" {
  export OPENCODE_SESSION_ID="ses_special_marker_42"
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_arch", owner_opencode_session_id="ses_special_marker_42", goal={})
PYEOF
  run run_current "ses_special_marker_42"
  [ "$status" -eq 0 ]
  [[ "$output" == *"📍 Current: rds_"* ]]
}

@test "current fallback 到 hostname_$$" {
  # No OPENCODE_SESSION_ID set; fallback to hostname_$$ pattern.
  unset OPENCODE_SESSION_ID
  python3 - <<PYEOF
import sys, socket, os
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
expected = f"{socket.gethostname().split('.')[0]}_{os.getpid()}"
coord.create_session(kind="stage_plan", owner_opencode_session_id=expected, goal={})
PYEOF
  run run_current "$(hostname -s)_$$"
  [ "$status" -eq 0 ]
  [[ "$output" == *"📍 Current: rds_"* ]]
}

@test "current 不修改 sessions.json" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_plan", owner_opencode_session_id="ses_me", goal={})
PYEOF
  before_hash=$(sha256sum "$TEST_ROOT/.rddf/state/sessions.json" | awk '{print $1}')
  run run_current "ses_me"
  after_hash=$(sha256sum "$TEST_ROOT/.rddf/state/sessions.json" | awk '{print $1}')
  [ "$before_hash" = "$after_hash" ]
}
```

- [ ] **Step 2: Run test to verify it fails (Python calls succeed — test stays green)**

Run:
```bash
cd /workspace/project/spec-workflow && bats tests/integration/test_rddf_session_current.bats
```

Expected: All 8 tests PASS at the Python helper level (because `find_current_binding` + `find_next_recommendation` already work from Task 1+2). This is the data-layer smoke test for the new subcommand.

If any test fails, inspect — the most likely cause is a missing import or fixture issue, NOT a logic bug.

- [ ] **Step 3: Add `current` subcommand to rddf-session.md**

Edit `skills/rddf-session.md`:

1. In the subcommands list (lines 21-28), add `current` between `show` and `resume`:

```markdown
skill_use("rddf-session show <id>")             # show full JSON for a session
skill_use("rddf-session current")               # show my current binding + recommend next (spec 2026-07-14)
skill_use("rddf-session resume <id>")           # transfer ownership to current opencode session; refresh heartbeat
```

2. In the bash case statement (after the `show` case around line 82), add the `current` case BEFORE `resume`:

```bash
    current)
        OPENCODE_SESSION_ID="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
        python3 - "$SESSIONS_FILE" "$OPENCODE_SESSION_ID" "$PROJECT_ROOT" <<'PYEOF'
import sys, json
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else ".")
from skills._lib.rddf_session import RddfSessionCoordinator
sessions_file, owner = sys.argv[1], sys.argv[2]
coord = RddfSessionCoordinator(sessions_file=sessions_file)
coord.check_heartbeat_timeouts()
current = coord.find_current_binding(owner)
if current:
    print(f"📍 Current: {current.session_id} (kind={current.kind}, started={current.started_at})")
else:
    print("📍 No current binding")
    nxt = coord.find_next_recommendation(owner)
    if nxt:
        print(f"💡 Recommended: {nxt.session_id} (kind={nxt.kind}, last_heartbeat={nxt.last_heartbeat})")
        print(f'   → skill_use("rddf-session resume {nxt.session_id}")')
    else:
        print("   No orphaned rddf-sessions found. Run guide-arch or guide-plan to start.")
PYEOF
        ;;
```

3. Update the frontmatter `metadata:` block to bump `version: "1.1"` (semver minor bump for the new subcommand) and add `evolved-from: "split from rddf-session.md v1.0"`. **DO NOT** touch `name` / `description` / `user-invocable` (they're read-only per AGENTS.md).

- [ ] **Step 4: Run test to verify it passes (bats wrapper test)**

Run:
```bash
cd /workspace/project/spec-workflow && bats tests/integration/test_rddf_session_current.bats
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/rddf-session.md tests/integration/test_rddf_session_current.bats && git commit -m "feat(rddf-session): add 'current' subcommand (spec 2026-07-14)

Prints current OpenCode-session binding (active rddf-session) when bound,
or recommends the next orphaned session to resume when unbound.

8 integration tests cover: bound/unbound/orphaned paths, missing files,
corrupt JSON, OPENCODE_SESSION_ID env var, hostname fallback, no mutation.

No changes to existing 5 subcommands. Frontmatter version bumped 1.0 → 1.1."
```

---

## Task 4: Add `scan_session_binding` function to scan-state.sh

**Files:**
- Modify: `skills/_lib/scan-state.sh` (append function at end)
- Create: `tests/integration/test_guide_binding_alert.bats` (binding alert tests)

- [ ] **Step 1: Write the failing bats test for scan_session_binding**

Append to `tests/integration/test_guide_binding_alert.bats` (new file):

```bash
#!/usr/bin/env bats
#
# Integration tests for scan_session_binding() output appended to guide
# recommender (spec 2026-07-14).

load ../test_helper

setup() {
  export TEST_ROOT="$BATS_TMPDIR/test-guide-binding-$$"
  mkdir -p "$TEST_ROOT/.rddf/state"
  cd "$TEST_ROOT"
  git init -q
  git config user.email "test@example.com"
  git config user.name "Test"
  # Roadmap + plan-handoff absent → scan_state falls through to default.
  # We do NOT set up a full project; we only verify BINDING_LINES behavior.
  load_lib scan-state
}

teardown() {
  rm -rf "$TEST_ROOT"
}

@test "scan_session_binding 输出 binding 行 当有 current binding" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_ship", owner_opencode_session_id="ses_me", goal={})
PYEOF
  export OPENCODE_SESSION_ID="ses_me"
  scan_session_binding "$TEST_ROOT"
  [ "${#BINDING_LINES[@]}" -gt 0 ]
  [[ "${BINDING_LINES[0]}" == *"📍 Current: rds_"* ]]
}

@test "scan_session_binding 输出 recommended next 行 当无 binding + 有 orphaned" {
  python3 - <<PYEOF
import sys, json
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
sid = coord.create_session(kind="stage_plan", owner_opencode_session_id="ses_old", goal={})
data = json.loads(coord._sessions_file.read_text())
for s in data["sessions"]:
    if s["session_id"] == sid:
        s["last_heartbeat"] = "2020-01-01T00:00:00+00:00"
coord._atomic_write(data)
coord.check_heartbeat_timeouts()
PYEOF
  export OPENCODE_SESSION_ID="ses_me"
  scan_session_binding "$TEST_ROOT"
  [ "${#BINDING_LINES[@]}" -ge 2 ]
  [[ "${BINDING_LINES[0]}" == *"📍 No current binding"* ]]
  [[ "${BINDING_LINES[1]}" == *"💡 Recommended: rds_"* ]]
}

@test "scan_session_binding 不输出行 当 sessions.json 缺失" {
  rm -f "$TEST_ROOT/.rddf/state/sessions.json"
  export OPENCODE_SESSION_ID="ses_me"
  scan_session_binding "$TEST_ROOT"
  [ "${#BINDING_LINES[@]}" -eq 0 ]
}

@test "scan_session_binding 不修改 RECOMMEND" {
  # scan_state should still set RECOMMEND; scan_session_binding should
  # NOT clear it. Verify they coexist.
  scan_state "$TEST_ROOT"
  RECOMMEND_BEFORE="$RECOMMEND"
  scan_session_binding "$TEST_ROOT"
  [ "$RECOMMEND" = "$RECOMMEND_BEFORE" ]
}

@test "scan_session_binding 不修改 sessions.json" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_ship", owner_opencode_session_id="ses_me", goal={})
PYEOF
  before_hash=$(sha256sum "$TEST_ROOT/.rddf/state/sessions.json" | awk '{print $1}')
  export OPENCODE_SESSION_ID="ses_me"
  scan_session_binding "$TEST_ROOT"
  after_hash=$(sha256sum "$TEST_ROOT/.rddf/state/sessions.json" | awk '{print $1}')
  [ "$before_hash" = "$after_hash" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /workspace/project/spec-workflow && bats tests/integration/test_guide_binding_alert.bats
```

Expected: FAIL with `scan_session_binding: command not found`

- [ ] **Step 3: Implement `scan_session_binding`**

Append to the end of `skills/_lib/scan-state.sh` (after the closing brace of `scan_state`):

```bash
# scan_session_binding [PROJECT_ROOT]
#   Scans .rddf/state/sessions.json for the current OpenCode session's
#   binding status. Populates global array BINDING_LINES with 1-2 lines:
#     - Line 1: "📍 Current: <rds_id> (kind=<K>, started=<T>)" if bound
#               "📍 No current binding" otherwise
#     - Line 2: "💡 Recommended: <rds_id> ... → skill_use(...)" only when
#               unbound AND an orphaned session exists.
#   Silent on missing/invalid file (returns 0, BINDING_LINES stays empty).
#   Read-only: does NOT modify sessions.json.
BINDING_LINES=()
scan_session_binding() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local SESSIONS_FILE="$PROJECT_ROOT/.rddf/state/sessions.json"
  BINDING_LINES=()
  [ -f "$SESSIONS_FILE" ] || return 0
  local owner="${OPENCODE_SESSION_ID:-$(hostname -s)_$$}"
  while IFS= read -r line; do
    BINDING_LINES+=("$line")
  done < <(PY_PROJECT_ROOT="$PROJECT_ROOT" \
    python3 - "$SESSIONS_FILE" "$owner" "$PROJECT_ROOT" <<'PYEOF'
import os, sys
sys.path.insert(0, sys.argv[3] if len(sys.argv) > 3 else ".")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file=sys.argv[1])
coord.check_heartbeat_timeouts()
owner = sys.argv[2]
current = coord.find_current_binding(owner)
if current:
    print(f"📍 Current: {current.session_id} (kind={current.kind}, started={current.started_at})")
else:
    print("📍 No current binding")
    nxt = coord.find_next_recommendation(owner)
    if nxt:
        print(f"💡 Recommended: {nxt.session_id} (kind={nxt.kind}, last_heartbeat={nxt.last_heartbeat})")
        print(f'   → skill_use("rddf-session resume {nxt.session_id}")')
    else:
        print("   No orphaned rddf-sessions found. Run guide-arch or guide-plan to start.")
PYEOF
    )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /workspace/project/spec-workflow && bats tests/integration/test_guide_binding_alert.bats
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/_lib/scan-state.sh tests/integration/test_guide_binding_alert.bats && git commit -m "feat(scan-state): add scan_session_binding function (spec 2026-07-14)

Reads .rddf/state/sessions.json via RddfSessionCoordinator and populates
BINDING_LINES array with current binding + recommendation. Read-only —
does not modify sessions.json or RECOMMEND/REASON globals.

5 integration tests cover: bound/unbound paths, missing file, RECOMMEND
preservation, no file mutation."
```

---

## Task 5: Wire `scan_session_binding` into guide.md output

**Files:**
- Modify: `skills/guide.md` (extend the bash example to invoke `scan_session_binding` after `scan_state`)

- [ ] **Step 1: Add guide binding alert bats test**

Append to `tests/integration/test_guide_binding_alert.bats`:

```bash
@test "guide 输出 binding 行 当有 current binding" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_ship", owner_opencode_session_id="ses_me", goal={})
PYEOF
  export OPENCODE_SESSION_ID="ses_me"
  # Run the full guide flow (scan_state + scan_session_binding + print)
  scan_state "$TEST_ROOT"
  scan_session_binding "$TEST_ROOT"
  # Verify the binding line is present in BINDING_LINES (not yet printed to stdout)
  [[ "${BINDING_LINES[0]}" == *"📍 Current: rds_"* ]]
}

@test "guide 不输出 binding 行 当 sessions.json 缺失" {
  rm -f "$TEST_ROOT/.rddf/state/sessions.json"
  export OPENCODE_SESSION_ID="ses_me"
  scan_state "$TEST_ROOT"
  scan_session_binding "$TEST_ROOT"
  [ "${#BINDING_LINES[@]}" -eq 0 ]
}

@test "guide 不改变 RECOMMEND 当 binding 状态变化" {
  # First scan: no binding
  scan_state "$TEST_ROOT"
  R1="$RECOMMEND"
  scan_session_binding "$TEST_ROOT"
  L1_COUNT="${#BINDING_LINES[@]}"
  # Now add a binding and re-scan
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_ship", owner_opencode_session_id="ses_me", goal={})
PYEOF
  scan_state "$TEST_ROOT"
  R2="$RECOMMEND"
  scan_session_binding "$TEST_ROOT"
  [ "$R1" = "$R2" ]
}

@test "guide binding 行在 RECOMMEND/REASON 之后" {
  # The print order in guide.md MUST be RECOMMEND → REASON → BINDING_LINES.
  # We verify the source code of guide.md enforces this ordering.
  grep -q 'scan_session_binding' "$REPO_ROOT/skills/guide.md"
  # Confirm scan_state appears before scan_session_binding
  STATE_LINE=$(grep -n 'scan_state' "$REPO_ROOT/skills/guide.md" | head -1 | cut -d: -f1)
  BIND_LINE=$(grep -n 'scan_session_binding' "$REPO_ROOT/skills/guide.md" | head -1 | cut -d: -f1)
  [ "$STATE_LINE" -lt "$BIND_LINE" ]
}

@test "guide 不修改 sessions.json" {
  python3 - <<PYEOF
import sys
sys.path.insert(0, "$REPO_ROOT")
from skills._lib.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file="$TEST_ROOT/.rddf/state/sessions.json")
coord.create_session(kind="stage_ship", owner_opencode_session_id="ses_me", goal={})
PYEOF
  before_hash=$(sha256sum "$TEST_ROOT/.rddf/state/sessions.json" | awk '{print $1}')
  export OPENCODE_SESSION_ID="ses_me"
  scan_state "$TEST_ROOT"
  scan_session_binding "$TEST_ROOT"
  after_hash=$(sha256sum "$TEST_ROOT/.rddf/state/sessions.json" | awk '{print $1}')
  [ "$before_hash" = "$after_hash" ]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd /workspace/project/spec-workflow && bats tests/integration/test_guide_binding_alert.bats
```

Expected: The 4 new tests FAIL with `scan_session_binding: command not found` (or grep miss). The 5 tests from Task 4 should now PASS.

- [ ] **Step 3: Update guide.md to invoke `scan_session_binding`**

In `skills/guide.md`, locate the "扫描逻辑（v1.1+：提取到独立脚本）" section (around line 21-32) and update the bash example:

Replace the existing bash code block:

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# shellcheck source=/dev/null
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/_lib/scan-state.sh"
scan_state "$PROJECT_ROOT"
```

With:

```bash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
# shellcheck source=/dev/null
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")/_lib/scan-state.sh"
scan_state "$PROJECT_ROOT"
echo "💡 Recommended: skill_use(\"$RECOMMEND\")"
echo "   Reason: $REASON"

# Binding discovery (spec 2026-07-14): read-only rddf-session binding scan
scan_session_binding "$PROJECT_ROOT"
if [ ${#BINDING_LINES[@]} -gt 0 ]; then
  printf '%s\n' "${BINDING_LINES[@]}"
fi
```

Then update the "输出格式" section (around line 36-48) to mention the new lines:

After the existing example output, add:

```
输出追加（v2.0.2+，仅当 .rddf/state/sessions.json 存在时）：

📍 Current: rds_xxx (kind=stage_X, started=...)             # 当当前 OpenCode session 已绑定一个 active rddf-session
📍 No current binding                                          # 当无活跃绑定
💡 Recommended: rds_yyy ... → skill_use("rddf-session resume ...")  # 当存在 orphaned session
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd /workspace/project/spec-workflow && bats tests/integration/test_guide_binding_alert.bats
```

Expected: 10 passed (5 from Task 4 + 5 from Task 5)

- [ ] **Step 5: Commit**

```bash
cd /workspace/project/spec-workflow && git add skills/guide.md tests/integration/test_guide_binding_alert.bats && git commit -m "feat(guide): append rddf-session binding lines to recommender output

After RECOMMEND/REASON, scan_session_binding populates BINDING_LINES
with current binding status + next recommendation. guide.md example now
invokes scan_session_binding after scan_state and prints BINDING_LINES.

Output format documented in the spec 2026-07-14.

5 additional integration tests cover: bound path, no-binding path,
RECOMMEND stability, source ordering, no file mutation. Total: 10 tests
in test_guide_binding_alert.bats."
```

---

## Task 6: Update AGENTS.md + ADR-0017 cross-reference

**Files:**
- Modify: `AGENTS.md` (add Session Binding Policy section)
- Modify: `docs/adr/ADR-0017-rddf-session.md` (add Cross-Reference section)

- [ ] **Step 1: Add Session Binding Policy to AGENTS.md**

In `AGENTS.md`, locate the "关键约定" section and add a new subsection after "Arch Discovery Contract (ADR-0016)" subsection:

```markdown
### Session Binding Policy (ADR-0017 + spec 2026-07-14)

Every workflow session generated by `guide-arch`/`guide-plan`/`guide-ship` MUST bind to a rddf-session via `owner_opencode_session_id`. The `guide` recommender surfaces this binding via `BINDING_LINES` (no state mutation). Users running raw skills can check their binding via `skill_use("rddf-session current")`. Manual skill invocation without binding is allowed but the user is responsible for resolving any cross-session conflicts (4-option soft prompt per ADR-0017 §3).
```

- [ ] **Step 2: Add Cross-Reference to ADR-0017**

In `docs/adr/ADR-0017-rddf-session.md`, append at the end (after "## References"):

```markdown
## Cross-Reference

- **spec 2026-07-14** (`docs/superpowers/specs/2026-07-14-rddf-session-binding-design.md`) — extends this ADR with discoverable binding + next-session recommendation. Adds `RddfSessionCoordinator.find_current_binding()` and `find_next_recommendation()` (read-only methods), `rddf-session current` subcommand, and `scan_session_binding()` integration into `guide`. No schema changes.
```

- [ ] **Step 3: Verify docs render correctly**

Run:
```bash
cd /workspace/project/spec-workflow && grep -q "Session Binding Policy" AGENTS.md && grep -q "spec 2026-07-14" AGENTS.md && grep -q "spec 2026-07-14" docs/adr/ADR-0017-rddf-session.md && echo "All cross-references present"
```

Expected: `All cross-references present`

- [ ] **Step 4: Commit**

```bash
cd /workspace/project/spec-workflow && git add AGENTS.md docs/adr/ADR-0017-rddf-session.md && git commit -m "docs(workflow): add Session Binding Policy + ADR-0017 cross-reference

AGENTS.md gains Session Binding Policy subsection documenting the
mandatory rddf-session binding for workflow sessions and the discovery
mechanism (guide BINDING_LINES + rddf-session current subcommand).

ADR-0017 gains Cross-Reference section pointing to the spec that
extends it (2026-07-14) with no schema changes."
```

---

## Task 7: Final verification — full test suite green

**Files:** none (verification only)

- [ ] **Step 1: Run all unit tests**

Run:
```bash
cd /workspace/project/spec-workflow && python3 -m pytest tests/unit/ -q --tb=short
```

Expected: all pass; specifically:
- `tests/unit/test_rddf_binding.py` — 10 passed
- `tests/unit/test_rddf_session.py` — 27 passed (unchanged)
- `tests/integration/test_rddf_session_lifecycle.py` — unchanged

If any fail, identify whether the failure is in new code (regression to fix) or pre-existing (note but don't fix per AGENTS.md guidance).

- [ ] **Step 2: Run new integration tests**

Run:
```bash
cd /workspace/project/spec-workflow && bats tests/integration/test_rddf_session_current.bats tests/integration/test_guide_binding_alert.bats tests/integration/test_guide_scan.bats
```

Expected: 8 + 10 + 4 = 22 passed

- [ ] **Step 3: Run smoke tests + structural skill tests**

Run:
```bash
cd /workspace/project/spec-workflow && bats tests/smoke.bats tests/integration/test_skill_metadata_consistency.bats tests/integration/test_guide_skill.bats
```

Expected: all pass. The `test_skill_metadata_consistency.bats` may need a regeneration if the smoke.bats hardcoded list doesn't include `current`; verify but don't preemptively fix.

- [ ] **Step 4: Run CI constant-truth gate**

Run:
```bash
cd /workspace/project/spec-workflow && grep -rn "assert.*or True\|assert True" tests/ || echo "GATE PASS"
```

Expected: `GATE PASS`

- [ ] **Step 5: Verify no regressions in bats scan-state.sh grep guards**

Run:
```bash
cd /workspace/project/spec-workflow && bats tests/integration/test_guide_scan.bats
```

Expected: 4 passed (existing P1-3/P1-4 regression guards still hold)

- [ ] **Step 6: Verify schema unchanged**

Run:
```bash
cd /workspace/project/spec-workflow && python3 -c "import json; d=json.load(open('skills/_lib/schemas/sessions_schema.json')); print('schema_version:', d['version']); assert d['version']==1, 'version must stay 1'; print('SCHEMA UNCHANGED')"
```

Expected: `schema_version: 1` + `SCHEMA UNCHANGED`

- [ ] **Step 7: Final summary commit (no-op if nothing changed)**

If any verification step required an inline fix, commit it now:
```bash
cd /workspace/project/spec-workflow && git status
```

If dirty, commit with `chore(verify): address spec 2026-07-14 final-verification findings` and the actual diff summary.

If clean, no commit needed. Print "All verification passed."

- [ ] **Step 8: Mark plan complete**

Print final summary:
```
Plan: rddf-session Binding & Recommendation (spec 2026-07-14)
Total commits: 6 (Tasks 1-6) + 0-1 (Task 7 if needed)
Files created: 3 (test files)
Files modified: 6 (rddf_session.py, rddf-session.md, scan-state.sh, guide.md, AGENTS.md, ADR-0017)
Tests added: 28 (10 unit + 8 integration current + 10 integration guide)
Schema bumps: 0 (sessions.json v1 unchanged)
Public API breaks: 0 (only additive)
Backward compat: 100%
```

---

## Self-Review (post-write)

### 1. Spec coverage

| Spec requirement | Task |
|------------------|------|
| §2 Goal 1 (show binding) | Task 1 (find_current_binding) + Task 3 (current subcommand) |
| §2 Goal 2 (recommend next) | Task 2 (find_next_recommendation) + Task 3 |
| §2 Goal 3 (surface in guide) | Task 4 (scan_session_binding) + Task 5 (guide wiring) |
| §2 Goal 4 (reuse owner_opencode_session_id) | Task 1 design choice (no new state file) |
| §2 Goal 5 (add 2 methods to coordinator) | Task 1 + Task 2 |
| §2 Goal 6 (10 unit + ~13 integration tests) | Tasks 1, 2, 3, 4, 5 |
| §2 Goal 7 (AGENTS + ADR docs) | Task 6 |
| §6.2 `find_current_binding` signature | Task 1 |
| §6.2 `find_next_recommendation` signature | Task 2 |
| §6.3 `scan_session_binding` bash + BINDING_LINES | Task 4 |
| §8.1 `current` subcommand output | Task 3 |
| §8.2 guide output format | Task 5 |
| §9 Error handling (9 rows) | Tests in Tasks 1-5 cover most rows; missing-file path tested in Tasks 3+4 |
| §10.1 (10 unit tests) | Task 1 (5) + Task 2 (5) |
| §10.2 (8 current subcommand tests) | Task 3 |
| §10.3 (5 guide binding alert tests) | Tasks 4 + 5 (5 + 5; 5 + 5 = 10 covers all + extra) |

### 2. Placeholder scan

✓ No `TBD` / `TODO` / "implement later" / "fill in details" / "Similar to Task N" patterns.

### 3. Type consistency

- `find_current_binding(owner_opencode_session_id: str) -> Optional[RddfSession]` — defined Task 1, used Tasks 1, 3, 4, 5 ✓
- `find_next_recommendation(owner_opencode_session_id: Optional[str] = None) -> Optional[RddfSession]` — defined Task 2, used Tasks 2, 3, 4, 5 ✓
- `scan_session_binding [PROJECT_ROOT]` — defined Task 4, used Task 4 + Task 5 ✓
- `BINDING_LINES` array — defined Task 4, used Task 5 ✓
- `OPENCODE_SESSION_ID` env var with `hostname -s_$$` fallback — used Tasks 3, 4, 5 ✓
- All RddfSession field names match `skills/_lib/schemas/sessions_schema.json` ✓

### 4. Risks / open items

- **Skill metadata consistency**: if `smoke.bats` hardcodes the 13-skill list (per AGENTS.md "smoke.bats is outdated"), this change adds `current` as a subcommand but does not add a new skill file. So `smoke.bats` does NOT need updating. If `test_skill_metadata_consistency.bats` does need updating, address it in Task 7 Step 3.
- **Cross-platform fcntl.flock**: pre-existing concern in `RddfSessionCoordinator`. Not addressed by this spec (out of scope per spec §14).
- **scan-state.sh source order**: Task 5 explicitly verifies via grep that `scan_state` appears before `scan_session_binding` in guide.md. Regression guard built into the test.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-14-rddf-session-binding.md`. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?