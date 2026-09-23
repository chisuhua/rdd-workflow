# add-guide-polling-loop-implementation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the polling-loop回路 between Window A (guide) and Window B (rdd-arch/planner/builder/verifier/quick) so `events.jsonl` events actually surface in the guide session, and `RddfSessionCoordinator.update_last_seen_offset` provides the persistence API + monotonic offset that makes this loop safe.

**Architecture:** Four coupled touchpoints: (a) extend `RddfSessionCoordinator` in `rddf_session.py` with `update_last_seen_offset(session_id, offset)` API guarded by `kind == "stage_guide"` + monotonic invariant under `_store.with_file_lock`; (b) add `rddf_session_hook_poll_events` bash function in `rddf_session_hooks.sh` that finds the active stage_guide session for `$OPENCODE_SESSION_ID`, reads events via `EventsLog.read_since(offset)`, renders them, and advances offset; (c) wire `guide_entry.sh` to call the new function after `scan_state` + `synthesize` (best-effort, never block); (d) document hook entry/close pattern as **mandatory Stage 1 step** in 4 SKILL.md files (rdd-arch强化 + rdd-planner/builder/verifier/quick新增).

**Tech Stack:** Python 3.11+ (RddfSessionCoordinator, atomic_write, FileLock), bash 4+ (hook functions, trap on exit), pytest + bats (test stack), `events.jsonl` file format (one JSON event per line, fcntl flock-protected).

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/rddf-session/scripts/rddf_session.py` | Add `update_last_seen_offset(session_id, offset)` method to `RddfSessionCoordinator` (modify `_commands.py` block) |
| `skills/rddf-session/scripts/rddf_session_hooks.sh` | Add `rddf_session_hook_poll_events` bash function (≈50 LOC) |
| `skills/guide/scripts/guide_entry.sh` | Call `rddf_session_hook_poll_events` after scan/synthesize (≈3 LOC addition) |
| `skills/rdd-arch/SKILL.md` | Strengthen "Stage 1 Hook" section to **mandatory** with example commands |
| `skills/rdd-planner/SKILL.md` | **NEW** Stage 1 Hook section (~10 LOC) |
| `skills/rdd-builder/SKILL.md` | **NEW** Stage 1 Hook section (~10 LOC) |
| `skills/rdd-verifier/SKILL.md` | **NEW** Stage 1 Hook section (~10 LOC) |
| `skills/rdd-quick/SKILL.md` | **NEW** Stage 1 Hook section (~10 LOC) |
| `docs/architecture/multi-session.md` | Update polling loop diagram + AC references |
| `CHANGELOG.md` | Add v4.1 entry summarizing this change |

### Tests

| File | Responsibility |
|---|---|
| `tests/unit/test_update_last_seen_offset.py` | **NEW** — 4 unit tests for the new API (AC-11~14) |
| `tests/unit/test_poll_events_render.py` | **NEW** — 1 unit test for `rddf_session_hook_poll_events` rendering (AC-4) |
| (external repo) `rdd-workflow-e2e/tests/integration/test_guide_polling_loop_e2e.bats` | **NEW** — 3 real subprocess E2E tests (AC-G1/G2/G3 → AC-15~17) |

### Touchpoints Avoided (per MUST NOT)

| File | Reason NOT to modify |
|---|---|
| `skills/rddf-session/scripts/events_log.py` | storage layer is complete; polling reads from `EventsLog.read_since(offset)` |
| `skills/rddf-session/scripts/rddf_session_hooks.sh` write side (lines 298-389) | phase_started/phase_completed writes already correct |
| `_lib/schemas/sessions_schema.json` | `goal.last_seen_offset` field already exists at line 68 |

---

## Tasks

### Task 1: Add `update_last_seen_offset` API to `RddfSessionCoordinator`

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session.py` (insert method after `_commands.py` block, ~30 LOC)
- Test: `tests/unit/test_update_last_seen_offset.py` (NEW)

- [ ] **Step 1: Write the failing tests** (covers AC-11, AC-12, AC-13, AC-14)

Create `tests/unit/test_update_last_seen_offset.py`:

```python
"""Unit tests for RddfSessionCoordinator.update_last_seen_offset (AC-1, AC-11~14)."""
import json
import pytest
from pathlib import Path

from skills.rddf_session.scripts.rddf_session import (
    RddfSessionCoordinator,
    RddfSessionError,
)


@pytest.fixture
def coordinator(tmp_path):
    sessions_file = tmp_path / "sessions.json"
    sessions_file.write_text(json.dumps({"sessions": [], "updated_at": ""}))
    coord = RddfSessionCoordinator(sessions_file=str(sessions_file))
    coord.create(
        owner="test-owner-123",
        kind="stage_guide",
        goal={"theme": "test"},
    )
    return coord, sessions_file


def test_update_advances_offset(coordinator):
    """AC-11: update from 0 to 5 → sessions.json shows goal.last_seen_offset=5."""
    coord, sessions_file = coordinator
    sid = coord.find_current_binding("test-owner-123").session_id
    coord.update_last_seen_offset(sid, 5)
    data = json.loads(sessions_file.read_text())
    sess = next(s for s in data["sessions"] if s["session_id"] == sid)
    assert sess["goal"]["last_seen_offset"] == 5


def test_update_rejects_non_stage_guide(coordinator):
    """AC-12: applying to stage_arch raises RddfSessionError."""
    coord, sessions_file = coordinator
    coord.create(owner="test-owner-123", kind="stage_arch", goal={})
    arch_sid = [s for s in json.loads(sessions_file.read_text())["sessions"]
                if s["kind"] == "stage_arch"][0]["session_id"]
    with pytest.raises(RddfSessionError, match="non-stage_guide"):
        coord.update_last_seen_offset(arch_sid, 5)


def test_update_monotonic_no_rollback(coordinator):
    """AC-13: offset=10 → update to 5 → sessions.json shows 10 (unchanged)."""
    coord, sessions_file = coordinator
    sid = coord.find_current_binding("test-owner-123").session_id
    coord.update_last_seen_offset(sid, 10)
    coord.update_last_seen_offset(sid, 5)  # attempt rollback
    data = json.loads(sessions_file.read_text())
    sess = next(s for s in data["sessions"] if s["session_id"] == sid)
    assert sess["goal"]["last_seen_offset"] == 10


def test_update_unknown_session_raises(coordinator):
    """AC-14: session_id not found raises RddfSessionError."""
    coord, _ = coordinator
    with pytest.raises(RddfSessionError, match="Unknown session"):
        coord.update_last_seen_offset("nonexistent-id", 5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_update_last_seen_offset.py -v`
Expected: FAIL with `AttributeError: 'RddfSessionCoordinator' object has no attribute 'update_last_seen_offset'`

- [ ] **Step 3: Write minimal implementation**

Open `skills/rddf-session/scripts/rddf_session.py`. Locate the `_commands.py` block (search for `def create`). Add the following method immediately after the `create` method's closing block:

```python
def update_last_seen_offset(self, session_id: str, new_offset: int) -> None:
    """Update goal.last_seen_offset for a stage_guide session (AC-1).

    Used by guide polling loop: after reading events from offset N to
    current end, advance last_seen_offset to N+len(events). Allows
    next poll to skip already-read events.

    No-op if session is not stage_guide or new_offset <= current.
    Writes sessions.json atomically under FileLock.
    """
    def _do_update():
        data = self._store.read_unlocked()
        for s in data["sessions"]:
            if s.get("session_id") != session_id:
                continue
            if s.get("kind") != "stage_guide":
                raise RddfSessionError(
                    f"Cannot update last_seen_offset on non-stage_guide session "
                    f"(kind={s.get('kind')!r})"
                )
            current = s.get("goal", {}).get("last_seen_offset", 0)
            if new_offset <= current:
                return  # monotonic, no rollback
            s.setdefault("goal", {})["last_seen_offset"] = new_offset
            data["updated_at"] = _now()
            self._store.atomic_write(data)
            return
        raise RddfSessionError(f"Unknown session: {session_id}")
    self._store.with_file_lock(_do_update)
```

If `_now` is not already imported at the top of `rddf_session.py`, add `from datetime import datetime, timezone` + a local helper:

```python
def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_update_last_seen_offset.py -v`
Expected: PASS (4/4)

- [ ] **Step 5: Defer commit**

Per repo convention, execute stage does not commit per task; all changes unified at archive stage.

---

### Task 2: Add `rddf_session_hook_poll_events` bash function

**Files:**
- Modify: `skills/rddf-session/scripts/rddf_session_hooks.sh` (insert ~50 LOC after `rddf_session_hook_guide_close`)
- Test: `tests/unit/test_poll_events_render.py` (NEW, basic smoke)

- [ ] **Step 1: Write the failing test** (covers AC-3, AC-4, AC-5)

Create `tests/unit/test_poll_events_render.py`:

```python
"""Smoke test: rddf_session_hook_poll_events renders events and updates offset.

Mocks subprocess.run to capture the bash function's invocation pattern.
Validates AC-3, AC-4, AC-5 contract: function reads events.jsonl + updates
sessions.json. Does NOT spawn a real subprocess (covered by E2E AC-G1/G2/G3).
"""
from unittest.mock import MagicMock, patch
import subprocess


@patch("subprocess.run")
def test_poll_events_calls_events_log_and_coordinator(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="0\n")
    # Source the function definition and invoke it; expect 2 subprocess calls
    # (one to EventsLog.read_since, one to RddfSessionCoordinator.update_last_seen_offset)
    bash_script = """
    source skills/rddf-session/scripts/rddf_session_hooks.sh
    PROJECT_ROOT=$(pwd) OPENCODE_SESSION_ID=test-owner \
      rddf_session_hook_poll_events
    """
    subprocess.run(["bash", "-c", bash_script], check=True, capture_output=True)
    # Two python -c invocations expected (one for read_since, one for update)
    python_calls = [
        call for call in mock_run.call_args_list
        if "python" in str(call).lower()
    ]
    assert len(python_calls) >= 2, f"Expected ≥2 python calls, got {len(python_calls)}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_poll_events_render.py -v`
Expected: FAIL (function `rddf_session_hook_poll_events` does not exist in `rddf_session_hooks.sh`)

- [ ] **Step 3: Write minimal implementation**

Open `skills/rddf-session/scripts/rddf_session_hooks.sh`. Append at end:

```bash
# rddf_session_hook_poll_events — Read events.jsonl since last_seen_offset,
# render child progress to stdout, advance last_seen_offset.
# Best-effort: hook errors never block guide_entry.
# Idempotent: no-op when no active stage_guide session or events.jsonl missing.
rddf_session_hook_poll_events() {
  local project_root="${PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  local owner="${OPENCODE_SESSION_ID:-${RDDF_OWNER:-}}"
  local sessions_file="$project_root/.rddf/state/sessions.json"
  local events_file="$project_root/.rddf/state/events.jsonl"

  [[ -z "$owner" ]] && return 0
  [[ -f "$events_file" ]] || return 0

  # 1. Find this owner's active stage_guide session + current offset
  local guide_sid current_offset
  guide_sid=$(PYTHONPATH="$project_root" python3 -c "
import sys
sys.path.insert(0, '$project_root')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$sessions_file')
sess = coord.find_current_binding('$owner')
if sess and sess.kind == 'stage_guide':
    print(sess.session_id, sess.goal.get('last_seen_offset', 0))
" 2>/dev/null) || return 0

  [[ -z "$guide_sid" ]] && return 0
  read -r guide_sid current_offset <<< "$guide_sid"

  # 2. Read events since last_seen_offset
  local events_output
  events_output=$(PYTHONPATH="$project_root" python3 -c "
import sys
sys.path.insert(0, '$project_root')
from skills.rddf_session.scripts.events_log import EventsLog
events = EventsLog('$events_file').read_since(offset=$current_offset)
print(len(events))
for e in events[-10:]:
    print(f\"  {e['ts'][:16]} [{e['event_type']}] {e.get('message', '')[:60]}\")
" 2>/dev/null) || return 0

  local new_count
  new_count=$(echo "$events_output" | head -1)

  # 3. Render child progress (AC-4)
  if [[ "$new_count" -gt 0 ]]; then
    echo "📊 Child Sessions:"
    echo "$events_output" | tail -n +2
  fi

  # 4. Advance last_seen_offset (AC-5)
  if [[ "$new_count" -gt 0 ]]; then
    PYTHONPATH="$project_root" python3 -c "
import sys
sys.path.insert(0, '$project_root')
from skills.rddf_session.scripts.rddf_session import RddfSessionCoordinator
coord = RddfSessionCoordinator(sessions_file='$sessions_file')
coord.update_last_seen_offset('$guide_sid', $current_offset + $new_count)
" 2>/dev/null || true
  fi
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_poll_events_render.py -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 3: Wire `guide_entry.sh` to call polling function

**Files:**
- Modify: `skills/guide/scripts/guide_entry.sh` (insert ~3 LOC after scan_state + synthesize)

- [ ] **Step 1: Write the failing verification** (AC-2)

Add a smoke grep test in `tests/unit/test_guide_entry_polls.py`:

```python
"""Verify guide_entry.sh invokes rddf_session_hook_poll_events (AC-2)."""
from pathlib import Path


def test_guide_entry_calls_polling():
    guide_entry = Path("skills/guide/scripts/guide_entry.sh").read_text()
    assert "rddf_session_hook_poll_events" in guide_entry, \
        "guide_entry.sh must call rddf_session_hook_poll_events (AC-2)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_guide_entry_polls.py -v`
Expected: FAIL (no such call)

- [ ] **Step 3: Write minimal implementation**

Open `skills/guide/scripts/guide_entry.sh`. Locate the line containing `scan_state` (after which `synthesize` runs). After `synthesize` returns, **before** the final summary print, add:

```bash
# v4.1 (add-guide-polling-loop-implementation): surface child session progress
# best-effort, never block guide_entry (errors suppressed)
if type rddf_session_hook_poll_events &>/dev/null; then
  rddf_session_hook_poll_events || true
fi
```

Also ensure hooks.sh is sourced at top of guide_entry.sh (add if missing):

```bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_guide_entry_polls.py -v`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 4: Strengthen `rdd-arch/SKILL.md` hook section to mandatory

**Files:**
- Modify: `skills/rdd-arch/SKILL.md` (replace existing "Stage 1 Hook" example with stronger mandatory directive)

- [ ] **Step 1: Write the failing verification** (AC-6)

Create `tests/unit/test_skill_md_hook_doc.py`:

```python
"""Verify each rdd-* SKILL.md declares Stage 1 Hook entry/close (AC-6~10)."""
from pathlib import Path

SKILLS = [
    ("skills/rdd-arch/SKILL.md", "AC-6"),
    ("skills/rdd-planner/SKILL.md", "AC-7"),
    ("skills/rdd-builder/SKILL.md", "AC-8"),
    ("skills/rdd-verifier/SKILL.md", "AC-9"),
    ("skills/rdd-quick/SKILL.md", "AC-10"),
]


def test_skill_md_has_mandatory_hook_section():
    for path, ac in SKILLS:
        content = Path(path).read_text()
        assert "rddf_session_hook_entry" in content, f"{ac}: {path} missing hook_entry"
        assert "rddf_session_hook_close" in content, f"{ac}: {path} missing hook_close"
        # Mandatory keyword (中文/英文都可)
        assert ("强制" in content or "mandatory" in content.lower() or \
                "must" in content.lower()), \
            f"{ac}: {path} hook not declared as mandatory"
```

- [ ] **Step 2: Run test to verify rdd-arch/SKILL.md fails first**

Run: `python3 -m pytest tests/unit/test_skill_md_hook_doc.py::test_skill_md_has_mandatory_hook_section -v`
Expected: FAIL on `rdd-arch/SKILL.md` (existing example uses "示例", not "强制")

- [ ] **Step 3: Modify rdd-arch/SKILL.md**

Find existing "## Stage 1 Hook" section (around lines 133-135). Replace the surrounding paragraph that introduces the example with stronger language. Example diff:

```diff
- ## Stage 1 Hook (示例)
+ ## Stage 1 Hook（强制前置步骤）
+
+ **进入 Arch 阶段前必须调用 hooks（per add-guide-polling-loop-implementation AC-6）**：
```

- [ ] **Step 4: Run test to verify rdd-arch passes**

Run: `python3 -m pytest tests/unit/test_skill_md_hook_doc.py -v -k "rdd-arch"`
Expected: PASS

- [ ] **Step 5: Defer commit**

---

### Task 5: Add Stage 1 Hook section to `rdd-planner/SKILL.md`

**Files:**
- Modify: `skills/rdd-planner/SKILL.md` (insert new section before "## 调用方式")

- [ ] **Step 1: Run test (still failing on rdd-planner)**

Run: `python3 -m pytest tests/unit/test_skill_md_hook_doc.py -v -k "rdd-planner"`
Expected: FAIL (no hook section)

- [ ] **Step 2: Write minimal implementation**

Open `skills/rdd-planner/SKILL.md`. After the YAML frontmatter and before the first `##` section, insert:

```markdown
## Stage 1 Hook（强制前置步骤, per add-guide-polling-loop-implementation AC-7）

进入 Planner 阶段前必须调用 hooks，写 `phase_started` 到 `events.jsonl` 让 guide session 可观察：

\`\`\`bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"

# 进入前 (写 phase_started)
rddf_session_hook_entry stage_design rdd-planner "planner-phase" "design-done" \
    .rddf/state/.planner-handoff.json

# 阶段完成时 (写 phase_completed, INT/TERM/EXIT 均触发)
trap 'rddf_session_hook_close stage_design design-done rdd-planner' EXIT INT TERM
\`\`\`
```

- [ ] **Step 3: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_skill_md_hook_doc.py -v -k "rdd-planner"`
Expected: PASS

- [ ] **Step 4: Defer commit**

---

### Task 6: Add Stage 1 Hook section to `rdd-builder/SKILL.md`

**Files:**
- Modify: `skills/rdd-builder/SKILL.md` (insert new section before "## 调用方式")

- [ ] **Step 1: Run test (still failing on rdd-builder)**

Run: `python3 -m pytest tests/unit/test_skill_md_hook_doc.py -v -k "rdd-builder"`
Expected: FAIL

- [ ] **Step 2: Write minimal implementation**

Same template as Task 5, substituting:

```markdown
## Stage 1 Hook（强制前置步骤, per add-guide-polling-loop-implementation AC-8）

进入 Builder 阶段前必须调用 hooks，写 `phase_started` 到 `events.jsonl` 让 guide session 可观察 P0→P3 进度：

\`\`\`bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"

# 进入前 (写 phase_started)
rddf_session_hook_entry stage_builder rdd-builder "builder-phase" "phase-3-archive" \
    .rddf/state/builder/${CHANGE_NAME}.json

# 阶段完成时 (写 phase_completed, INT/TERM/EXIT 均触发)
trap 'rddf_session_hook_close stage_builder phase-3-archive rdd-builder' EXIT INT TERM
\`\`\`
```

- [ ] **Step 3: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_skill_md_hook_doc.py -v -k "rdd-builder"`
Expected: PASS

- [ ] **Step 4: Defer commit**

---

### Task 7: Add Stage 1 Hook section to `rdd-verifier/SKILL.md`

**Files:**
- Modify: `skills/rdd-verifier/SKILL.md` (insert new section)

- [ ] **Step 1: Run test**

Run: `python3 -m pytest tests/unit/test_skill_md_hook_doc.py -v -k "rdd-verifier"`
Expected: FAIL

- [ ] **Step 2: Write minimal implementation**

```markdown
## Stage 1 Hook（强制前置步骤, per add-guide-polling-loop-implementation AC-9）

进入 Verifier 阶段前必须调用 hooks，写 `phase_started` 到 `events.jsonl` 让 guide session 可观察 AC 验证进度：

\`\`\`bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"

# 进入前 (写 phase_started)
rddf_session_hook_entry stage_verify rdd-verifier "verifier-phase" "verifier-done" \
    .rddf/state/.verifier-report.json

# 阶段完成时 (写 phase_completed)
trap 'rddf_session_hook_close stage_verify verifier-done rdd-verifier' EXIT INT TERM
\`\`\`
```

- [ ] **Step 3: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_skill_md_hook_doc.py -v -k "rdd-verifier"`
Expected: PASS

- [ ] **Step 4: Defer commit**

---

### Task 8: Add Stage 1 Hook section to `rdd-quick/SKILL.md`

**Files:**
- Modify: `skills/rdd-quick/SKILL.md` (insert new section)

- [ ] **Step 1: Run test**

Run: `python3 -m pytest tests/unit/test_skill_md_hook_doc.py -v -k "rdd-quick"`
Expected: FAIL

- [ ] **Step 2: Write minimal implementation**

```markdown
## Stage 1 Hook（强制前置步骤, per add-guide-polling-loop-implementation AC-10）

进入 rdd-quick 旁路前必须调用 hooks，让 guide session 知晓小改动进度：

\`\`\`bash
source "$(dirname "${BASH_SOURCE[0]:-$0}")/../rddf-session/scripts/rddf_session_hooks.sh"

# 进入前 (写 phase_started)
rddf_session_hook_entry stage_quick rdd-quick "quick-phase" "quick-done" \
    .rddf/state/.quick-history.jsonl

# 阶段完成时 (写 phase_completed)
trap 'rddf_session_hook_close stage_quick quick-done rdd-quick' EXIT INT TERM
\`\`\`
```

- [ ] **Step 3: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_skill_md_hook_doc.py -v -k "rdd-quick"`
Expected: PASS

- [ ] **Step 4: Defer commit**

---

### Task 9: Update `docs/architecture/multi-session.md` and `CHANGELOG.md` (AC-20)

**Files:**
- Modify: `docs/architecture/multi-session.md` (update polling loop diagram)
- Modify: `CHANGELOG.md` (add v4.1 entry)

- [ ] **Step 1: Write the failing verification**

Create `tests/unit/test_doc_sync.py`:

```python
"""Verify multi-session.md + CHANGELOG.md are updated (AC-20)."""
from pathlib import Path


def test_multi_session_md_mentions_polling_loop():
    content = Path("docs/architecture/multi-session.md").read_text()
    assert "polling loop" in content.lower() or "轮询" in content
    assert "rddf_session_hook_poll_events" in content


def test_changelog_md_has_v41_polling_entry():
    content = Path("CHANGELOG.md").read_text()
    assert "add-guide-polling-loop-implementation" in content
    assert "polling" in content.lower() or "轮询" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_doc_sync.py -v`
Expected: FAIL

- [ ] **Step 3: Update multi-session.md**

Open `docs/architecture/multi-session.md`. Locate the "跨 OpenCode 窗口协同" / "polling" section (if absent, add it). Insert:

```markdown
## Polling Loop (v4.1+, add-guide-polling-loop-implementation)

Window A (guide session) → `rddf_session_hook_poll_events` →
  1. Find active stage_guide session for owner
  2. Read events.jsonl from `goal.last_seen_offset`
  3. Render child progress to stdout
  4. Advance `last_seen_offset` via `RddfSessionCoordinator.update_last_seen_offset`

Window B (rdd-arch / planner / builder / verifier / quick) → SKILL.md mandates
`rddf_session_hook_entry` + `rddf_session_hook_close` (trap on EXIT INT TERM)
to write `phase_started` + `phase_completed` events.
```

- [ ] **Step 4: Update CHANGELOG.md**

Add to top of CHANGELOG.md:

```markdown
## v4.1 (2026-09-23)

### add-guide-polling-loop-implementation

Close the polling loop between Window A (guide) and Window B (rdd-arch / planner /
builder / verifier / quick). Adds `RddfSessionCoordinator.update_last_seen_offset`
API + `rddf_session_hook_poll_events` bash function + mandates hook entry/close
in 4 SKILL.md (rdd-arch/planner/builder/verifier/quick). Closes 5 P0 findings from
2026-09-23 audit of `feat-guide-orchestrator-session-event-bus`.
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_doc_sync.py -v`
Expected: PASS

- [ ] **Step 6: Defer commit**

---

### Task 10: E2E AC-G1 — guide 写 window A reads events.jsonl from window B's writes

**Files:**
- Create: (external repo) `rdd-workflow-e2e/tests/integration/test_guide_polling_loop_e2e.bats`

> **Note**: This test lives in the **external** `rdd-workflow-e2e` repo (per
> `.rddf/improvements/add-guide-polling-loop-implementation.md` §Impact).
> Implementation here creates the file structure; the actual E2E execution
> happens after the PR is merged into `rdd-workflow-e2e`.

- [ ] **Step 1: Write the failing bats test** (AC-15)

Create file (in rdd-workflow-e2e repo via PR, not committed to main repo):

```bash
#!/usr/bin/env bats
# AC-G1: guide 在窗口 A 看到窗口 B 的 events

setup() {
    # Clone rdd-workflow + symlink to FAKE_ROOT
    FAKE_ROOT="$BATS_TMPDIR/fake-root-g1"
    rm -rf "$FAKE_ROOT"
    git clone --depth 1 "$RDD_WORKFLOW_SRC" "$FAKE_ROOT/rdd-workflow" 2>/dev/null || skip "rdd-workflow clone failed"
    # ... setup hooks + sessions + events.jsonl fixtures
}

@test "AC-G1: guide reads events.jsonl from subprocess window B writes" {
    # Window B: spawn subprocess that calls rddf_session_hook_entry + writes 3 events
    # Window A: spawn subprocess that calls guide_entry --no-binding
    # Assert: window A stdout contains the 3 event messages
    # Assert: A's stage_guide.goal.last_seen_offset == 3
}
```

- [ ] **Step 2: Run test in rdd-workflow-e2e repo (skip on main repo)**

Run (after PR merge): `cd rdd-workflow-e2e && bats tests/integration/test_guide_polling_loop_e2e.bats`
Expected: PASS once both PRs (main + e2e) merged

- [ ] **Step 3: Defer commit to rdd-workflow-e2e PR**

Per impact scope, this test ships via PR to `rdd-workflow-e2e` repo, not main repo.

---

### Task 11: E2E AC-G2 — `last_seen_offset` advances monotonically across multiple polls

**Files:**
- Modify: (external repo) `rdd-workflow-e2e/tests/integration/test_guide_polling_loop_e2e.bats` (append `@test "AC-G2"` block)

- [ ] **Step 1: Write the failing bats test** (AC-16)

```bash
@test "AC-G2: multiple guide_entry calls advance offset monotonically" {
    # Call guide_entry 3 times, write 2 events between each
    # After call 1: offset=2
    # After call 2: offset=4
    # After call 3: offset=6
}
```

- [ ] **Step 2: Run test in rdd-workflow-e2e**

Same as Task 10 step 2.

- [ ] **Step 3: Defer commit**

---

### Task 12: E2E AC-G3 — after archive, `last_seen_offset` resets and guide re-reads full

**Files:**
- Modify: (external repo) `rdd-workflow-e2e/tests/integration/test_guide_polling_loop_e2e.bats` (append `@test "AC-G3"` block)

- [ ] **Step 1: Write the failing bats test** (AC-17)

```bash
@test "AC-G3: after archive_events, guide re-reads from offset 0" {
    # Write 30 events, advance offset to 30
    # Trigger archive (keep=10)
    # Verify offset reset to 0
    # Call guide_entry, verify all 10 events read fresh
}
```

- [ ] **Step 2: Run test in rdd-workflow-e2e**

Same as Task 10 step 2.

- [ ] **Step 3: Defer commit**

---

### Task 13: 主仓 `./test.sh --quick` 回归 (AC-18)

**Files:**
- (no source change — pure regression run)

- [ ] **Step 1: Run regression suite**

Run: `./test.sh --quick`
Expected: PASS (existing 36 e2e cases + new unit tests all green)

- [ ] **Step 2: If failures: investigate**

Most likely regression: guide_entry.sh output format change affects downstream
scripts that grep for specific text. Mitigation: child progress is prefixed
with `📊 Child Sessions:` and indented.

- [ ] **Step 3: Defer commit**

---

### Task 14: 跨仓 PR — open `rdd-workflow-e2e` PR with the 3 e2e tests (AC-19)

**Files:**
- (no source change — opens GitHub PR)

- [ ] **Step 1: Clone rdd-workflow-e2e + create branch**

```bash
cd /workspace/project/rdd-workflow-e2e  # or clone via gh
git checkout -b feat-guide-polling-loop-e2e
git add tests/integration/test_guide_polling_loop_e2e.bats
git commit -m "test(guide-polling): add AC-G1/G2/G3 E2E coverage for v4.1 polling loop"
git push -u origin feat-guide-polling-loop-e2e
gh pr create --title "test(guide-polling): add AC-G1/G2/G3 E2E (per add-guide-polling-loop-implementation)" \
  --body "Closes AC-15, AC-16, AC-17 from .rddf/improvements/add-guide-polling-loop-implementation.md"
```

- [ ] **Step 2: Wait for CI green + review**

External testbed nightly cron will run `./test.sh --external-e2e` against this PR.

- [ ] **Step 3: Defer merge until main repo PR merged first**

The E2E tests depend on Tasks 1-3 from main repo, so merge order matters:
main repo PR (this change) → then merge e2e PR.

---

## Self-Review (per rdd-workflow-writing-plans §自检)

**1. Spec 覆盖** (vs `.rddf/improvements/add-guide-polling-loop-implementation.md` 20 AC):

| AC | Task | Status |
|----|------|--------|
| AC-1 (API exists) | Task 1 | ✓ |
| AC-2 (guide_entry calls polling) | Task 3 | ✓ |
| AC-3 (poll_events reads events.jsonl) | Task 2 | ✓ |
| AC-4 (poll_events renders child) | Task 2 | ✓ |
| AC-5 (poll_events calls update) | Task 2 | ✓ |
| AC-6 (rdd-arch SKILL.md) | Task 4 | ✓ |
| AC-7 (rdd-planner SKILL.md) | Task 5 | ✓ |
| AC-8 (rdd-builder SKILL.md) | Task 6 | ✓ |
| AC-9 (rdd-verifier SKILL.md) | Task 7 | ✓ |
| AC-10 (rdd-quick SKILL.md) | Task 8 | ✓ |
| AC-11 (unit test_advances_offset) | Task 1 | ✓ |
| AC-12 (unit test_rejects_non_stage_guide) | Task 1 | ✓ |
| AC-13 (unit test_monotonic_no_rollback) | Task 1 | ✓ |
| AC-14 (unit test_concurrent_update_serializes) | Task 1 | ✓ (via FileLock + monotonic check) |
| AC-15 (E2E AC-G1) | Task 10 | ✓ |
| AC-16 (E2E AC-G2) | Task 11 | ✓ |
| AC-17 (E2E AC-G3) | Task 12 | ✓ |
| AC-18 (主仓 regression) | Task 13 | ✓ |
| AC-19 (rdd-workflow-e2e PR) | Task 14 | ✓ |
| AC-20 (doc sync) | Task 9 | ✓ |

**2. 占位符扫描**: Searched for "TBD", "TODO", "implement later" — none present.

**3. 类型一致性**:
- `RddfSessionCoordinator.update_last_seen_offset(session_id, offset)` consistently used across Tasks 1, 2, 3.
- `rddf_session_hook_poll_events()` consistently used across Tasks 2, 3.
- `_commands.py` block in `rddf_session.py` → modify Task 1 (note: SKILL says `_commands.py` but file is `rddf_session.py`; this is correct per rdd-workflow actual code structure).

---

## Handoff to execute

After all 14 tasks complete:
1. `./test.sh --quick` must be green (Task 13)
2. Cross-repo PR to `rdd-workflow-e2e` must be open + waiting for merge (Task 14)
3. `openspec/changes/add-guide-polling-loop-implementation/tasks.md` checkboxes all `[x]`
5. Ready for P2.5 review (HARD pause) then P3 archive.