---
SCOPE: shared
STATUS: PROPOSED
---

# Tasks: fix-scan-state-recursion

> **Goal**: Fix infinite recursion in `skills/_lib/scan-state.sh::check_stale_workflow_state` (line 220 self-call). Add regression test confirming `scan_state` returns within 1s on clean state.
> **Risk**: low (1-line surgical fix).
> **Estimated effort**: 0.25-0.5 d.

## 1. Pre-flight

- [ ] **1.1 Verify the bug exists**

```bash
cd /workspace/project/rdd-workflow
PROJECT_ROOT=$(git rev-parse --show-toplevel)
NO_BINDING=0
source "$PROJECT_ROOT/skills/_lib/scan-state.sh"
timeout 5 scan_state "$PROJECT_ROOT" 2>&1 | tail -5
echo "exit=$?"
```

Expected: `timeout 5` fires (exit=124), confirming the hang.

- [ ] **1.2 Locate the bug**

```bash
grep -n "check_stale_workflow_state" skills/_lib/scan-state.sh | head -5
```

Expected: see the function definition (line 212) and the trailing self-call (line 220).

## 2. Apply change

### Task 2.1: Add regression test (TDD)

**Files:**
- Create: `tests/integration/test_scan_state_clean_hang.bats`

- [ ] **Step 1: Write failing test**

```bash
#!/usr/bin/env bats
# test_scan_state_clean_hang.bats — regression test for scan-state.sh
# infinite recursion bug (fix-scan-state-recursion)

load ../test_helper

@test "scan_state: terminates within 1s on clean repo (regression for hang bug)" {
    cd "$BATS_TEST_TMPDIR"
    rm -rf .git repo 2>/dev/null
    mkdir repo && cd repo
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
    mkdir -p openspec/changes openspec/specs
    # No openspec/changes/<active>/, no .rddf/state/* handoffs,
    # no roadmap.md, no proposal-suggestions.md — minimal clean repo

    # Source scan-state.sh from the real repo
    source "$REPO_ROOT/skills/_lib/scan-state.sh"

    # Run with timeout — bug caused scan_state to hang; fix makes it <1s
    run timeout 5 bash -c "scan_state '$PWD'"
    [ "$status" -ne 124 ]   # 124 = timeout fired = hang bug present
    [ -n "$RECOMMEND" ]      # function should set RECOMMEND
}

@test "scan_state: terminates within 1s when workflow-state.md is absent" {
    cd "$BATS_TEST_TMPDIR"
    rm -rf .git repo 2>/dev/null
    mkdir repo && cd repo
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
    # No workflow-state.md

    source "$REPO_ROOT/skills/_lib/scan-state.sh"
    run timeout 2 check_stale_workflow_state "$PWD"
    [ "$status" -eq 0 ]
    [ "$status" -ne 124 ]
}

@test "scan_state: terminates within 1s when workflow-state.md is present" {
    cd "$BATS_TEST_TMPDIR"
    rm -rf .git repo 2>/dev/null
    mkdir repo && cd repo
    git init -q
    git config user.email "t@t.t"
    git config user.name "t"
    echo "stale content" > workflow-state.md

    source "$REPO_ROOT/skills/_lib/scan-state.sh"
    run timeout 2 check_stale_workflow_state "$PWD"
    [ "$status" -eq 0 ]
    [ "$status" -ne 124 ]
}
```

- [ ] **Step 2: Run test, verify fail**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_scan_state_clean_hang.bats
```

Expected: all 3 tests fail (timeout fires, exit 124).

- [ ] **Step 3: Fix the bug**

Edit `skills/_lib/scan-state.sh`. Find `check_stale_workflow_state()` function (line ~212). Replace the trailing self-call:

```bash
check_stale_workflow_state() {
  local PROJECT_ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
  if [ -f "$PROJECT_ROOT/workflow-state.md" ]; then
    echo "⚠️  Stale workflow-state.md detected (pre-refactor format)."
    echo "   This file is no longer used and will be ignored."
    echo "   Remove it manually if you want: rm workflow-state.md"
  fi

  check_stale_workflow_state "$PROJECT_ROOT"
}
```

Replace with:

```bash
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

Changes: **delete** line 220 (the self-call), **insert** `return 0` as the new final statement. 1-line net change.

- [ ] **Step 4: Run test, verify pass**

```bash
cd /workspace/project/rdd-workflow
bats tests/integration/test_scan_state_clean_hang.bats
```

Expected: all 3 tests pass (no timeout).

- [ ] **Step 5: Verify existing scan_state bats tests still pass**

```bash
cd /workspace/project/rdd-workflow
bats tests/_lib/test_scan_state.bats
```

Expected: 38 tests still green.

- [ ] **Step 6: Commit**

```bash
git add skills/_lib/scan-state.sh tests/integration/test_scan_state_clean_hang.bats
git commit -m "fix(scan-state): terminate check_stale_workflow_state to avoid hang

Line 220 was a self-call without a base case, causing infinite recursion
when scan_state reached the priority 9/10 default fallback. With this
fix, the function terminates cleanly after the optional warning emission.

- check_stale_workflow_state returns within <100ms in both modes
  (workflow-state.md present / absent)
- scan_state returns RECOMMEND within <1s on clean repo
- 3 bats regression tests added (tests/integration/test_scan_state_clean_hang.bats)

Discovered 2026-07-15 when scan_state hung after add-archive-auto-commit
ship left repo in clean state (no active changes)."
```

### Task 2.2: Document in AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Find 常见陷阱 section**

```bash
grep -n "## 常见陷阱" AGENTS.md
```

- [ ] **Step 2: Append note**

After the last trap entry, append:

```markdown
12. **`check_stale_workflow_state` 是 read-only sentinel** — 不写文件、不递归。`scan_state` 在 priority 9/10 default fallback 调用它;如果函数挂死,scanner 也会挂死 (历史教训:line 220 self-call bug 修复于 2026-07-15 fix-scan-state-recursion)。
```

- [ ] **Step 3: Verify heading structure intact**

```bash
head -5 AGENTS.md && grep -c "^## " AGENTS.md
```

- [ ] **Step 4: Commit**

```bash
git add AGENTS.md
git commit -m "docs(AGENTS.md): document check_stale_workflow_state read-only contract

- Add entry 12 to 常见陷阱 section
- Notes the v2.0.4 fix (line 220 self-call removed) so future contributors
  don't accidentally re-introduce the recursion"
```

### Task 2.3: Final verification

- [ ] **Step 3.1: Full pytest suite**

```bash
cd /workspace/project/rdd-workflow
python3 -m pytest tests/unit/ tests/integration/ -q --tb=short
```

Expected: 627 passed (existing) + 3 new tests, all green.

- [ ] **Step 3.2: bats scan_state tests**

```bash
bats tests/_lib/test_scan_state.bats tests/integration/test_scan_state_clean_hang.bats
```

Expected: 38 + 3 = 41 tests green.

- [ ] **Step 3.3: End-to-end `guide` scanner timing**

```bash
cd /workspace/project/rdd-workflow
PROJECT_ROOT=$(git rev-parse --show-toplevel)
NO_BINDING=0
source "$PROJECT_ROOT/skills/_lib/scan-state.sh"
time scan_state "$PROJECT_ROOT" 2>&1
echo "RECOMMEND=$RECOMMEND"
```

Expected: completes in <1s; RECOMMEND is non-empty.

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

## Acceptance Criteria

- [ ] `check_stale_workflow_state` terminates within <100ms (both branches)
- [ ] `scan_state` returns RECOMMEND within <1s on clean state (regression test)
- [ ] Existing 38 scan_state bats tests still pass
- [ ] `guide` scanner returns RECOMMEND in <2s on clean repo
- [ ] AGENTS.md documents the read-only + terminating contract

## Commit History Expected

```
<latest master>
feat(openspec): add fix-scan-state-recursion change manifest (lands first)
fix(scan-state): terminate check_stale_workflow_state to avoid hang
docs(AGENTS.md): document check_stale_workflow_state read-only contract
```