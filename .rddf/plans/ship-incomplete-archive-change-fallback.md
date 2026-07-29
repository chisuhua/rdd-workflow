# ship-incomplete-archive-change-fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use skill_use("execute") to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 归档时自动将未完成任务转为 change 候选，防止任务丢失

**Architecture:** 在 archive 流程中增加 pre-archive check，扫描 tasks.md 未完成任务，自动生成 proposal-suggestions.md 条目

**Tech Stack:** Bash, Python, OpenSpec CLI

---

## File Structure

### Production Code

| File | Responsibility |
|---|---|
| `skills/_lib/archive.sh` | 增加 pre-archive 未完成任务检查函数 |
| `skills/guide-ship/scripts/ship_archive.sh` | 调用检查函数，展示候选列表 |

### Tests

| File | Responsibility |
|---|---|
| `tests/integration/test_ship_archive_incomplete.bats` | 测试有/无未完成任务的归档场景 |

---

### Task 1: 实现 pre-archive 未完成任务检查

**Files:**
- Modify: `skills/_lib/archive.sh`
- Test: `tests/integration/test_ship_archive_incomplete.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "archive: detects incomplete tasks and prompts for fallback" {
  # Setup: create change with incomplete tasks
  run archive_change "test-incomplete"
  [ "$status" -eq 1 ]
  [[ "$output" =~ "未完成任务" ]]
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_ship_archive_incomplete.bats`
Expected: FAIL - function not implemented

- [ ] **Step 3: Write minimal implementation**

```bash
# In archive.sh, add before archive_change():
check_incomplete_tasks() {
  local change_name="$1"
  local tasks_file="openspec/changes/$change_name/tasks.md"
  local incomplete_count=$(grep -c '^- \[ \]' "$tasks_file" 2>/dev/null || echo 0)
  [ "$incomplete_count" -gt 0 ] && return 1 || return 0
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_ship_archive_incomplete.bats`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/_lib/archive.sh tests/integration/test_ship_archive_incomplete.bats
git commit -m "feat: add pre-archive incomplete tasks check"
```

---

### Task 2: 实现 proposal-suggestions.md 自动追加

**Files:**
- Modify: `skills/guide-ship/scripts/ship_archive.sh`
- Test: `tests/integration/test_ship_archive_incomplete.bats`

- [ ] **Step 1: Write the failing test**

```bash
@test "archive: appends incomplete tasks to proposal-suggestions.md" {
  run archive_change "test-incomplete"
  grep -q "test-incomplete" proposal-suggestions.md
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bats tests/integration/test_ship_archive_incomplete.bats`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```bash
# In ship_archive.sh, after check_incomplete_tasks fails:
append_to_suggestions() {
  local change_name="$1"
  local task_desc="$2"
  echo "| $change_name | P2 | $(date +%Y-%m-%d) | 待讨论 |" >> proposal-suggestions.md
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bats tests/integration/test_ship_archive_incomplete.bats`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills/guide-ship/scripts/ship_archive.sh proposal-suggestions.md
git commit -m "feat: auto-append incomplete tasks to proposal-suggestions"
```
