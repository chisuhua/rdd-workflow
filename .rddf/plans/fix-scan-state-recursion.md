# fix-scan-state-recursion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix infinite recursion in `skills/_lib/scan-state.sh::check_stale_workflow_state` (line 220 self-call). Add regression test confirming `scan_state` returns within 1s on clean state. Document the read-only + terminating contract in AGENTS.md.

**Architecture:** Surgical 1-line fix in `scan-state.sh` (delete self-call, insert `return 0`). 3 bats regression tests using `timeout` to assert non-hanging. AGENTS.md note appended under 常见陷阱. No new modules.

**Tech Stack:** Bash 4+ (scan-state.sh), bats 1.10+ (integration tests), python 3.11+ (iteration.json updates).

**OpenSpec change artifacts** (canonical): `openspec/changes/fix-scan-state-recursion/{proposal,tasks}.md` + `specs/scan-state-clean-return/spec.md` (2 ADDED Requirements).

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/scan-state.sh` | MODIFY: line 220 self-call → `return 0` (1-line surgical fix) |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_scan_state_clean_hang.bats` | NEW: 3 regression tests using `timeout` to assert non-hang |

### Documentation

| File | Responsibility |
|---|---|
| `AGENTS.md` | MODIFY: append note to 常见陷阱 documenting the fix |

---

## Pre-flight

- [ ] **Verify the bug exists**

```bash
cd /workspace/project/rdd-workflow
PROJECT_ROOT=$(git rev-parse --show-toplevel)
source "$PROJECT_ROOT/skills/_lib/scan-state.sh"
timeout 3 scan_state "$PROJECT_ROOT" 2>&1 | head -3
echo "exit=$?  (124 = timeout fired = bug present)"
```

- [ ] **Locate the bug**

```bash
grep -n "check_stale_workflow_state" skills/_lib/scan-state.sh | head -5
```

Expected: see function definition (line 212) and trailing self-call (line 220).

---

### Task 1: Add bats regression test + apply 1-line fix (TDD)

**Files:** `tests/integration/test_scan_state_clean_hang.bats`, `skills/_lib/scan-state.sh`

- [ ] **Step 1.1: Write failing bats test**

Create `tests/integration/test_scan_state_clean_hang.bats`:

```bash
#!/usr/bin/env bats
# test_scan_state_clean_hang.bats — regression for scan-state.sh
# infinite recursion bug (line 220 self-call)

load ../test_helper

setup() {
    cd "$BATS_TEST_TMPDIR"
    rm -rf repo 2>/dev/null
    mkdir repo && cd repo
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
}

@test "scan_state: terminates within 3s on clean repo (regression for hang bug)" {
    # Clean state: openspec/changes/ but no active, no handoffs
    mkdir -p openspec/changes openspec/specs

    source "$REPO_ROOT/skills/_lib/scan-state.sh"
    run timeout 3 bash -c "scan_state '$PWD'"
    [ "$status" -ne 124 ]   # 124 = timeout fired = hang bug present
    [ -n "$RECOMMEND" ]
}

@test "check_stale_workflow_state: terminates when workflow-state.md is absent" {
    source "$REPO_ROOT/skills/_lib/scan-state.sh"
    run timeout 2 check_stale_workflow_state "$PWD"
    [ "$status" -eq 0 ]
    [ "$status" -ne 124 ]
}

@test "check_stale_workflow_state: terminates when workflow-state.md is present" {
    echo "stale content" > workflow-state.md
    source "$REPO_ROOT/skills/_lib/scan-state.sh"
    run timeout 2 check_stale_workflow_state "$PWD"
    [ "$status" -eq 0 ]
    [ "$status" -ne 124 ]
}
```

- [ ] **Step 1.2: Verify tests fail (red)**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_scan_state_clean_hang.bats
```

Expected: all 3 tests fail with timeout (exit 124).

- [ ] **Step 1.3: Apply the 1-line fix**

Edit `skills/_lib/scan-state.sh`. Find the `check_stale_workflow_state()` function (line 212-221). Replace the trailing self-call:

```bash
# OLD (line 220 — recursive self-call, infinite loop):
check_stale_workflow_state() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  if [ -f "$PROJECT_ROOT/workflow-state.md" ]; then
    echo "⚠️  Stale workflow-state.md detected (pre-refactor format)."
    echo "   This file is no longer used and will be ignored."
    echo "   Remove it manually if you want: rm workflow-state.md"
  fi

  check_stale_workflow_state "$PROJECT_ROOT"   # ← recursive!
}
```

With:

```bash
# NEW (terminate cleanly):
check_stale_workflow_state() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  if [ -f "$PROJECT_ROOT/workflow-state.md" ]; then
    echo "⚠️  Stale workflow-state.md detected (pre-refactor format)."
    echo "   This file is no longer used and will be ignored."
    echo "   Remove it manually if you want: rm workflow-state.md"
  fi
  return 0
}
```

Net change: **delete line 220, insert `return 0` as the new final statement**. 1-line diff.

- [ ] **Step 1.4: Verify tests pass (green)**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_scan_state_clean_hang.bats
```

Expected: all 3 tests pass.

- [ ] **Step 1.5: Verify existing scan_state bats tests still pass**

```bash
cd /workspace/project/rdd-workflow
bats tests/_lib/test_scan_state.bats 2>&1 | tail -3
```

Expected: 38 tests green.

- [ ] **Step 1.6: Commit**

```bash
git add skills/_lib/scan-state.sh tests/integration/test_scan_state_clean_hang.bats
git commit -m "fix(scan-state): terminate check_stale_workflow_state to avoid hang

Line 220 was a self-call without a base case, causing infinite recursion
when scan_state reached the priority 9/10 default fallback. With this
fix, the function terminates cleanly after the optional warning emission.

- check_stale_workflow_state returns within <100ms (both branches)
- scan_state returns RECOMMEND within <1s on clean repo
- 3 bats regression tests added (tests/integration/test_scan_state_clean_hang.bats)

Discovered 2026-07-15 when scan_state hung after add-archive-auto-commit
ship left repo in clean state (no active changes)."
```

---

### Task 2: Document fix in AGENTS.md

**Files:** `AGENTS.md`

- [ ] **Step 2.1: Find 常见陷阱 section**

```bash
grep -n "## 常见陷阱" AGENTS.md
```

- [ ] **Step 2.2: Append entry 12**

After the last trap entry (currently entry 11), append:

```markdown
12. **`check_stale_workflow_state` 是 read-only sentinel** — 不写文件、不递归。`scan_state` 在 priority 9/10 default fallback 调用它;若函数挂死,scanner 也会挂死(历史教训:line 220 self-call bug 修复于 2026-07-15 fix-scan-state-recursion)。
```

- [ ] **Step 2.3: Verify heading structure intact**

```bash
head -5 AGENTS.md && grep -c "^## " AGENTS.md
```

- [ ] **Step 2.4: Commit**

```bash
git add AGENTS.md
git commit -m "docs(AGENTS.md): document check_stale_workflow_state read-only contract

- Add entry 12 to 常见陷阱 section
- Notes the v2.0.4 fix (line 220 self-call removed) so future contributors
  don't accidentally re-introduce the recursion"
```

---

### Task 3: Final verification

- [ ] **Step 3.1: Full pytest suite**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/ tests/integration/ -q --tb=short
```

Expected: all green (627 + 3 new tests).

- [ ] **Step 3.2: bats regression tests**

```bash
cd /workspace/project/rdd-workflow
bats tests/_lib/test_scan_state.bats tests/integration/test_scan_state_clean_hang.bats 2>&1 | tail -5
```

Expected: 38 + 3 = 41 tests green.

- [ ] **Step 3.3: End-to-end scan_state timing**

```bash
cd /workspace/project/rdd-workflow
PROJECT_ROOT=$(git rev-parse --show-toplevel)
source "$PROJECT_ROOT/skills/_lib/scan-state.sh"
time scan_state "$PROJECT_ROOT" 2>&1 | tail -3
echo "RECOMMEND=$RECOMMEND"
```

Expected: completes in <1s; RECOMMEND non-empty.

- [ ] **Step 3.4: Update iteration.json**

```bash
python3 -c "
import sys, os
sys.path.insert(0, '/workspace/project/rdd-workflow')
from skills._lib import iteration as it_mod
data = it_mod.load('/workspace/project/rdd-workflow')
data = it_mod.add_or_update_change(data, name='fix-scan-state-recursion', status='completed')
it_mod.save('/workspace/project/rdd-workflow', data)
"
```

---

## Acceptance Criteria

- [ ] `check_stale_workflow_state` terminates within <100ms (both branches)
- [ ] `scan_state` returns RECOMMEND within <1s on clean state (regression test)
- [ ] Existing 38 scan_state bats tests still pass
- [ ] `guide` scanner returns RECOMMEND in <2s on clean repo
- [ ] AGENTS.md documents the read-only + terminating contract

## Commit History Expected

```
03598ab (master base) feat(openspec): add fix-scan-state-recursion change
fix(scan-state): terminate check_stale_workflow_state to avoid hang
docs(AGENTS.md): document check_stale_workflow_state read-only contract
```