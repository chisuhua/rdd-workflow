#!/usr/bin/env bats
# tests/integration/test_rdd_quick_archive_compat.bats
# Integration tests for skills/rdd-quick/scripts/generate_tasks_md.py
# Per rdd-workflow v2.1 fix: rdd-quick mode a archive gate compatibility.
#
# Coverage:
#  - script existence + executable
#  - Setup/Implementation/Verification 3-section structure
#  - Task N title preservation
#  - All items use [x] (one-shot, not [ ])
#  - Idempotency: skip if tasks.md exists
#  - Exit codes (success / missing args)

load 'test_helper'

setup() {
    PROJECT_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/../.." && pwd)"
    SCRIPT="$PROJECT_ROOT/skills/rdd-quick/scripts/generate_tasks_md.py"
    WORK_TMP="$(mktemp -d)"
    export CHANGE_NAME="test-change-$$"
    mkdir -p "$WORK_TMP/openspec/changes/$CHANGE_NAME"
    cat > "$WORK_TMP/openspec/changes/$CHANGE_NAME/proposal.md" <<'PROPOSAL'
# Test Proposal
## Why
Test
## Acceptance
- AC-1 test
PROPOSAL
    cat > "$WORK_TMP/plan-quick.md" <<'PLAN'
# Test Plan
**Goal:** Test goal
**Architecture:** Test architecture
**Tech Stack:** bash

---

### Task 1: First Task

**Files:**
- Create: foo.py

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Defer commit**

### Task 2: Second Task

**Files:**
- Modify: bar.py

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Write minimal implementation**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Defer commit**

### Task 3: Third Task

- [ ] **Step 1: Write the failing test**
PLAN
}

teardown() {
    rm -rf "$WORK_TMP"
}

@test "archive_compat: generate_tasks_md.py script exists and is executable" {
    [ -x "$SCRIPT" ]
}

@test "archive_compat: generates minimal tasks.md with Setup/Implementation/Verification sections" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --change "$CHANGE_NAME" --plan plan-quick.md --proposal "openspec/changes/$CHANGE_NAME/proposal.md"
    [ -f "openspec/changes/$CHANGE_NAME/tasks.md" ]
    [ "$(grep -c '^## 1. Setup' openspec/changes/$CHANGE_NAME/tasks.md)" = "1" ]
    [ "$(grep -c '^## 2. Implementation' openspec/changes/$CHANGE_NAME/tasks.md)" = "1" ]
    [ "$(grep -c '^## 3. Verification' openspec/changes/$CHANGE_NAME/tasks.md)" = "1" ]
}

@test "archive_compat: Implementation section contains all 3 Task titles" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --change "$CHANGE_NAME" --plan plan-quick.md --proposal "openspec/changes/$CHANGE_NAME/proposal.md"
    grep -qE "2\.[0-9]+ First Task" "openspec/changes/$CHANGE_NAME/tasks.md"
    grep -qE "2\.[0-9]+ Second Task" "openspec/changes/$CHANGE_NAME/tasks.md"
    grep -qE "2\.[0-9]+ Third Task" "openspec/changes/$CHANGE_NAME/tasks.md"
}

@test "archive_compat: all generated items use checkbox [x] (one-shot completion)" {
    cd "$WORK_TMP"
    python3 "$SCRIPT" --change "$CHANGE_NAME" --plan plan-quick.md --proposal "openspec/changes/$CHANGE_NAME/proposal.md"
    # No [ ] remaining, all completed
    ! grep -q "^- \[ \]" "openspec/changes/$CHANGE_NAME/tasks.md"
    # At least 5 [x] items (1 Setup + 3 Implementation + 2 Verification)
    [ "$(grep -c '^- \[x\]' openspec/changes/$CHANGE_NAME/tasks.md)" -ge 5 ]
}

@test "archive_compat: idempotent — skip if tasks.md exists" {
    cd "$WORK_TMP"
    echo "EXISTING CONTENT" > "openspec/changes/$CHANGE_NAME/tasks.md"
    python3 "$SCRIPT" --change "$CHANGE_NAME" --plan plan-quick.md --proposal "openspec/changes/$CHANGE_NAME/proposal.md"
    [ "$(cat openspec/changes/$CHANGE_NAME/tasks.md)" = "EXISTING CONTENT" ]
}

@test "archive_compat: exit code 0 on success, non-zero on missing args" {
    run python3 "$SCRIPT"
    [ "$status" != "0" ]
    cd "$WORK_TMP"
    python3 "$SCRIPT" --change "$CHANGE_NAME" --plan plan-quick.md --proposal "openspec/changes/$CHANGE_NAME/proposal.md"
    [ "$?" = "0" ]
}